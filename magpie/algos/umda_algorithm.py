import abc
import copy
import json
import random
import re
import subprocess

import magpie.core
import magpie.utils
from magpie.utils.ollama import ollama_generate
import requests
import time

from magpie.core import variant

# explanation given to the random patches that fill in when the LLM returns too few
RANDOM_FALLBACK = 'LLM returned too few patches, random fallback'





class UMDAAlgorithm(magpie.core.BasicAlgorithm):
    def __init__(self):
        super().__init__()
        self.name = 'UMDA Algorithm'
        self.config['pop_size'] = 20
        #self.config['selection_ratio'] = 0.5
        self.config['batch_reset'] = True
        self.config['max_examples'] = 10
        self.config['k_max'] = 2
        self.config['select'] = 'valid'
        self.examples = []  # list of (fitness, patch_str), sorted ascending — mirrors LLMAlgorithm

    def reset(self):
        super().reset()
        self.stats['gen'] = 0
        self.stats['eval_success'] = 0
        self.stats['eval_compile'] = 0
        self.stats['llm_patches_requested'] = 0
        self.stats['llm_missing_patches'] = 0
        self.stats['llm_malformed_patches'] = 0
        self.stats['llm_duplicate_patches'] = 0
        self.stats['sample_extra_edits'] = 0
        self.stats['sample_random_fallback'] = 0
        self.stats['sample_duplicates_kept'] = 0
        self.stats['gens_without_valid'] = 0
        self.examples = []

    def setup(self, config):
        super().setup(config)
        sec = config['search.eda']
        self.llm_model = sec['llm_model']
        self.llm_ip = sec['llm_ip']
        self.config['pop_size'] = int(sec['pop_size'])
        self.config['max_examples'] = int(sec.get('max_examples', fallback='10'))
        self.config['k_max'] = int(sec.get('k_max', fallback='2'))
        if self.config['k_max'] < 1:
            raise magpie.core.ScenarioError('[search.eda] k_max should be at least 1')
        self.config['select'] = sec.get('select', fallback='valid').strip().lower()
        if self.config['select'] not in ('valid', 'improving'):
            raise magpie.core.ScenarioError('[search.eda] select should be "valid" or "improving"')
       # self.config['selection_ratio'] = float(sec['selection_ratio'])
        tmp = sec['batch_reset'].lower()
        if tmp in ['true', 't', '1']:
            self.config['batch_reset'] = True
        elif tmp in ['false', 'f', '0']:
            self.config['batch_reset'] = False
        else:
            msg = '[search.umda] batch_reset should be Boolean'
            raise magpie.core.ScenarioError(msg)

    def run(self):
        distribution=None
        try:
            # initiate population of results and patches, and evaluate them
            self.hook_warmup()
            patches_population = self.initialize_population() #population is a list of Patch objects
            self.warmup()
            if self.report['stop']:
                return
            self.hook_start()

            start = time.perf_counter()

            #eval initial population
            runs_pop = {} #dictionary, indexed by solution (patch)
            generation_best_fitness = None
            for patch in patches_population:
                variant = magpie.core.Variant(self.software, patch)
                run = self.evaluate_variant(variant)
                self.update_vt_vc(run)
                accept, best, generation_best_fitness = self.updateBest(run, generation_best_fitness, patch)
                self.hook_evaluation(variant, run, accept, best)
                runs_pop[patch] = run
                self.stats['steps'] += 1 #steps son validaciones, max_steps en secenario indica numero maximo de evaluciones.

            self._update_examples(runs_pop)
            distribution = self._next_distribution(runs_pop, None)

            #run search loop
            while not self.stopping_condition(): #default based on #steps (that is, #evaluations) and time
                self.hook_main_loop()
                self.stats['gen'] += 1
                patches_population = self.sample_population(distribution, elitism=True)

                # eval each patch in the new population
                generation_best_fitness = None
                runs_pop.clear()

                for sol in patches_population:
                    if self.stopping_condition():
                        break
                    try:
                        variant = magpie.core.Variant(self.software, sol)
                    except Exception as e: print(sol)
                    run = self.evaluate_variant(variant)
                    self.update_vt_vc(run)
                    accept, best, generation_best_fitness = self.updateBest(run, generation_best_fitness, sol)
                    self.hook_evaluation(variant, run, accept, best)
                    runs_pop[sol] = run
                    self.stats['steps'] += 1

                self._update_examples(runs_pop)
                distribution = self._next_distribution(runs_pop, distribution)

            self.hook_search_time(start)
        except KeyboardInterrupt:
            self.report['stop'] = 'keyboard interrupt'
        finally:
            self.hook_vt_vc()
            self.hook_final_distribution(distribution)
            self.hook_sampling_stats()
            self.hook_llm_format_stats()
            self._hook_explanation_best_patch()
            self.hook_end()

    def _hook_explanation_best_patch(self):
        if self.report['best_patch'] is not None and self.llm_model not in (None, 'None'):
            patch_str = self.report['best_patch']
            try:
                explain_str = self.llm_explain_patch(patch_str)
            except Exception:
                explain_str = "Ollama service failed, no explanation available"
            self.software.logger.info("LLM Explanation of best patch: " + explain_str)


    def updateBest(self, run, local_best_fitness, sol):
        accept = best = False
        if run.status == 'SUCCESS':
            if self.dominates(run.fitness, local_best_fitness): #dominates generation best fitness
                local_best_fitness = run.fitness
                accept = True
                if self.dominates(run.fitness, self.report['best_fitness']): #dominates global best fitness
                    self.report['best_fitness'] = run.fitness
                    self.report['best_patch'] = sol
                    best = True
        return accept, best, local_best_fitness

    def aux_log_counter(self):
        gen = self.stats['gen']
        step = self.stats['steps']%self.config['pop_size']+1
        return f'{gen}-{step}'

    def initialize_population(self):
        population = []
        tries = magpie.settings.edit_retries
        expected = self.config['pop_size']
        while tries and len(population) < expected:
            sol = magpie.core.Patch()
            self.mutate(sol)
            if sol in population:
                tries -= 1
                continue
            population.append(sol)
        return population

    def mutate(self, patch):
        patch.edits.append(self.create_edit(self.software.noop_variant))

    #TODO: currently selects all success patches. The ideal for EDA is to select a percentage of the best patches.
    #although maybe selecting success patches is enough as filter.
    def select(self, pop):
        # select = valid: every variant that compiles and passes the tests and the run
        # oracle; select = improving: only those that are also faster than the original
        filtered = {sol for sol in pop if pop[sol].status == 'SUCCESS'}
        if self.config['select'] == 'improving':
            ref = self.report['reference_fitness']
            filtered = {sol for sol in filtered if self.dominates(pop[sol].fitness, ref)}
        return sorted(filtered, key=lambda sol: pop[sol].fitness)

    def _next_distribution(self, runs_pop, previous):
        # Learns the distribution from the valid variants of the generation. When there is
        # none, the previous distribution is kept (empty before the first valid variant,
        # which makes sample_population draw random 1-edit patches).
        distribution = self.estimate_distribution(self.select(runs_pop))
        if distribution:
            return distribution
        self.stats['gens_without_valid'] += 1
        self.software.logger.info('[search.umda] No valid variant in this generation: keeping the previous distribution')
        return previous or {}

    """
    Creates a pool of all edits (splits patches) that have been successful in the selected solutions.
    This pool is used to estimate the univariate distribution of each unique edit in the pool.
    If an edit appears in multiple patches, its frequency is counted as many times as it appears.
    
    (bivariate distributions could learn pairs of edits in the future).
    """
    def estimate_distribution(self, selected):
        # create a dict with the edit type as key and its frequency as value
        edits_unique = {}
        for sol in selected:
            for edit in sol.edits:
                edit_str = str(edit)
                if edit_str not in edits_unique:
                    edits_unique[edit_str] = 0
                edits_unique[edit_str] += 1

            # normalize the frequencies to probabilities
        total = sum(edits_unique.values())
        if total == 0: return {}
        prob_dict = {k: v / total for k, v in edits_unique.items()}

        return prob_dict



    def sample_population(self, edits_prob, elitism=False):
        """
        Samples a population of pop_size distinct patches (elite included) from the learnt
        marginal distribution of single edits (Algorithm 1 in the paper):
          1. a patch starts with one edit e ~ edits_prob;
          2. while it duplicates a patch already in the new population and has fewer than
             k_max edits, another edit e' ~ edits_prob, different from its current edits,
             is appended;
          3. if it still duplicates one, it is replaced by a random 1-edit patch that is not
             in the new population (_random_unique_patch).
        With an LLM, the LLM proposes the patches instead of steps 1-2, without the k_max
        limit; a malformed or duplicated one is replaced as in step 3. An empty distribution
        (no valid variant seen yet) yields random 1-edit patches.

        @param edits_prob: marginal probability of each edit (operation, target and
        ingredient) observed in the valid patches of the last generation.
        @param elitism: if True, the best patch found so far is kept in the new population.
        """
        population = []
        if elitism and self.report.get('best_patch'):
            population.append(copy.deepcopy(self.report['best_patch']))
        pop_size = int(self.config['pop_size'])

        if self.llm_model == 'None':  # sample from the distribution
            while len(population) < pop_size:
                population.append(self._sample_patch(edits_prob, population))
        else:  # use the LLM to propose the patches
            patches_list, explanations = self.llm_sample_population(edits_prob, pop_size - len(population))
            for patch_str, explanation in zip(patches_list, explanations):
                # a patch may contain one or several edits separated by |
                edit_str_list = [e.strip() for e in patch_str.split('|') if e.strip()]
                sol = magpie.core.Patch()
                try:
                    for edit_str in edit_str_list:
                        sol.edits.append(self._edit_from_str(edit_str))
                    # building the variant fails if some edit of the patch is invalid
                    magpie.core.Variant(self.software, sol)
                except (RuntimeError, ValueError, AssertionError, Exception):
                    self.software.logger.error('Error parsing edit from llm. Random 1-edit individual created.')
                    self.stats['llm_malformed_patches'] += 1
                    sol = None
                if sol is None or not sol.edits or self.isIn(sol, population):
                    # a well-formed patch from the LLM itself (not a missing one) that is
                    # empty or duplicated is also discarded, and counted apart
                    if sol is not None and explanation != RANDOM_FALLBACK:
                        self.stats['llm_duplicate_patches'] += 1
                    sol = self._random_unique_patch(population)
                population.append(sol)
        return population

    def _sample_patch(self, edits_prob, population):
        # Steps 1-3 of sample_population for one patch.
        if not edits_prob:
            return self._random_unique_patch(population)
        sol = magpie.core.Patch()
        used = []
        while True:
            candidates = [e for e in edits_prob if e not in used]
            if not candidates:
                break
            edit_str = random.choices(candidates, weights=[edits_prob[e] for e in candidates])[0]
            used.append(edit_str)
            sol.edits.append(self._edit_from_str(edit_str))
            if not self.isIn(sol, population) or len(sol.edits) >= self.config['k_max']:
                break
            self.stats['sample_extra_edits'] += 1
        if self.isIn(sol, population):
            sol = self._random_unique_patch(population)
        return sol

    def _random_unique_patch(self, population):
        # Random 1-edit patch not yet in the population; after edit_retries failed attempts
        # the last one is kept, and counted, so that the population still reaches pop_size.
        self.stats['sample_random_fallback'] += 1
        for _ in range(magpie.settings.edit_retries):
            sol = magpie.core.Patch()
            self.mutate(sol)
            if not self.isIn(sol, population):
                return sol
        self.stats['sample_duplicates_kept'] += 1
        return sol

    def llm_sample_population(self, edits_prob, pop_size):
        prompt = self._craft_population_prompt(edits_prob, pop_size)
        response_str = self._llm_call(prompt)
        patches, explanations = self._filter_llm_patches_and_explainations(response_str)
        self.stats['llm_patches_requested'] += pop_size
        # fill with random patches if LLM returned fewer than requested
        while len(patches) < pop_size:
            sol = magpie.core.Patch()
            self.mutate(sol)
            patches.append(str(sol))
            explanations.append(RANDOM_FALLBACK)
            self.stats['llm_missing_patches'] += 1
        return patches, explanations

    def llm_explain_patch(self, patch_str):
        sw_srcmodel = next(iter(self.software.noop_variant.models.items()))[1]
        sw_str = sw_srcmodel.dump()

        prompt = (f"Give a very brief explanation of the potential benefit in execution time of the following patch: {patch_str} \n"
                  f"in the following code:\n{sw_str}. Do not explain what I am trying to do nor the format of the patch. Just"
                  f"a 3-5 lines explanation of the potential benefit in execution time of the patch. ")

        response_str = self._llm_call(prompt)
        return response_str

    def _llm_call(self, prompt):
        # llm_ip may be "IP" (port 11434) or "IP:PORT"; failed requests are retried
        return ollama_generate(self.llm_ip, self.llm_model, prompt, logger=self.software.logger)



    def _llm_call2(self, prompt):
        url = "http://172.24.100.51:8080/v1/chat/completions"
        payload = {
            "model": "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
            "messages": [
                {
                    "role": "user",
                    "content": "say hi",
                }
            ],
            "max_tokens": 32,
        }

        result = subprocess.run(
            [
                "curl",
                "-v",
                url,
                "-H",
                "Content-Type: application/json",
                "-d",
                json.dumps(payload),
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )

        print("RETURN CODE:", result.returncode)
        print("STDOUT:")
        print(result.stdout)
        print("STDERR:")
        print(result.stderr)

    def _filter_llm_patches_and_explainations(self, response_str):
        matches = re.findall(
            r'^\s*(?:\d+\.\s*)?Patch\s*\d*:\s*(.+?)\s*[\r\n]+'
            r'\s*Explanation\s*\d*:\s*(.+?)(?=\s*[\r\n]+\s*(?:\d+\.\s*)?Patch\s*\d*:|\Z)',
            response_str,
            re.MULTILINE | re.DOTALL
        )

        patches = []
        explanations = []

        for patch, explanation in matches:
            patches.append(patch.strip())
            explanations.append(explanation.strip())
        return patches, explanations


    def _update_examples(self, runs_pop):
        for patch, run in runs_pop.items():
            if run.status == 'SUCCESS':
                self.examples.append((run.fitness, str(patch)))
        seen = set()
        unique = []
        for fitness, patch_str in self.examples:
            if patch_str not in seen:
                seen.add(patch_str)
                unique.append((fitness, patch_str))
        def sort_key(item):
            f = item[0]
            return f[0] if isinstance(f, list) else f
        unique.sort(key=sort_key)
        self.examples = unique[:self.config['max_examples']]

    def _craft_population_prompt(self, edits_probs, pop_size):
        sw_srcmodel = next(iter(self.software.noop_variant.models.items()))[1]
        sw_text = sw_srcmodel.dump()

        # Examples block — same as LLMAlgorithm
        if self.examples:
            examples_text = '\n'.join(
                f'{i+1}. {patch_str}  (fitness: {fitness})'
                for i, (fitness, patch_str) in enumerate(self.examples)
            )
            examples_block = (
                f'Here are the best patches found so far (lower fitness = faster execution):\n'
                f'{examples_text}\n\n'
                f'You may draw inspiration from these examples, but do not simply copy them. '
                f'Be creative in combining, extending, or modifying the edits shown.\n'
            )
        else:
            examples_block = (
                'No successful patches have been found yet. '
                'Generate novel patches based solely on the software below.\n'
            )

        # Distribution block — UMDA-specific addition
        if edits_probs:
            dist_lines = '\n'.join(
                f'  {edit}: {prob:.3f}'
                for edit, prob in sorted(edits_probs.items(), key=lambda x: -x[1])
            )
            distribution_block = (
                f'Additionally, here is the probability distribution of individual edits '
                f'learned from past successful patches (higher probability = more frequently useful):\n'
                f'{dist_lines}\n\n'
                f'Use this distribution as a guide, but feel free to combine edits creatively '
                f'or propose edits not listed in the distribution.\n\n'
            )
        else:
            distribution_block = ''

        prompt = (
            f'In the context of Genetic Improvement of software, I want to create {pop_size} new Patches '
            f'for the following original software.\n\n'
            f'Each patch contains 1 or more edits in the MAGPIE framework format '
            f'(XmlNodeDeletion, XmlNodeReplacement, or XmlNodeInsertion). '
            f'Multiple edits in a patch are separated by "|".\n\n'
            f'The fitness goal is to reduce the execution time of the original software.\n\n'
            f'This is the original software:\n{sw_text}\n\n'
            f'{examples_block}\n'
            f'{distribution_block}'
            f'Respect the required format, only reply with a numbered set of {pop_size} patch+explanation, '
            f'no further extra text. For instance:\n'
            f'Patch 1: XmlNodeDeletion<stmt>((\'file.xml\', \'stmt\', 3))\n'
            f'Explanation 1: Removes an unnecessary statement to reduce execution time.\n'
            f'Patch 2: XmlNodeDeletion<stmt>((\'file.xml\', \'stmt\', 5)) | '
            f'XmlNodeInsertion<stmt,block>((\'file.xml\', \'_inter_block\', 2), (\'file.xml\', \'stmt\', 1))\n'
            f'Explanation 2: Combines a deletion with an insertion to restructure a hot path.\n'
        )
        return prompt







    def isIn(self, sol, population):
        for p in population:
            if str(sol) == str(p): #__eq__ of abstract_edit has problems with equality of classes under WSL environment
                return True
        return False

    def _edit_from_str(self,edit_str):
        #edit_str = random.choices(list(edits_prob.keys()), weights=list(edits_prob.values()))[0]
        # get target and ingredient from sampled edit
        target = magpie.utils.convert.target_from_stringEdit(edit_str)
        ingredient = magpie.utils.convert.ingredient_from_stringEdit(edit_str)
        # create edit class and apply the target and ingredient

        if '<' in edit_str: #xml operators have <> (for C programs)
            edit_str = edit_str.split('>')[0]
            edit_str = edit_str + '>'
        else: edit_str = edit_str.split('(')[0]


        klass = magpie.utils.edit_from_string(edit_str)
        edit = klass.auto_create(self.software.noop_variant)
        edit.target = target
        if ingredient: edit.data = [ingredient]  # for InsertEdit or ReplaceEdit, needs list of tuple

        return edit

    def hook_main_loop(self):
        if self.config['batch_reset']:
            for a in self.config.get('batch_bins', []):
                random.shuffle(a)
            self.hook_reset_batch()

    def hook_search_time(self, start):
        end = time.perf_counter()
        msg = f'[search.umda] Search time: {end - start:.3f} seconds'
        self.software.logger.info(msg)



    def hook_final_distribution(self, distribution):
        # This hook can be used to log or process the final distribution of edits
        msg= f'[search.umda] Final distribution: \n'
        for edit, prob in (distribution or {}).items():
            msg += f'  {edit}: {prob:.4f}\n'
        msg += f'[search.umda] Total edits from successful patches: {len(distribution or {})}'
        self.software.logger.info(msg)

    def hook_sampling_stats(self):
        self.software.logger.info(
            f"[search.umda] Sampling: extra edits from the distribution: {self.stats['sample_extra_edits']}, "
            f"random 1-edit replacements: {self.stats['sample_random_fallback']}, "
            f"duplicates kept after retries: {self.stats['sample_duplicates_kept']}, "
            f"generations without valid variants: {self.stats['gens_without_valid']}"
        )

    def hook_llm_format_stats(self):
        if self.llm_model in (None, 'None'):
            return
        requested = self.stats.get('llm_patches_requested', 0)
        missing = self.stats.get('llm_missing_patches', 0)
        malformed = self.stats.get('llm_malformed_patches', 0)
        duplicate = self.stats.get('llm_duplicate_patches', 0)
        ratio_missing = (missing / requested) if requested else 0.0
        ratio_malformed = (malformed / requested) if requested else 0.0
        ratio_duplicate = (duplicate / requested) if requested else 0.0
        self.software.logger.info(
            f'[search.eda] LLM malformed patches: {malformed}/{requested} ({ratio_malformed:.3f}), '
            f'missing patches: {missing}/{requested} ({ratio_missing:.3f}), '
            f'duplicate patches: {duplicate}/{requested} ({ratio_duplicate:.3f})'
        )


magpie.utils.known_algos.append(UMDAAlgorithm)