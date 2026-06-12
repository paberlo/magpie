import abc
import copy
import json
import random
import re
import subprocess

import magpie.core
import magpie.utils
import requests
import time

from magpie.core import variant





class UMDAAlgorithm(magpie.core.BasicAlgorithm):
    def __init__(self):
        super().__init__()
        self.name = 'UMDA Algorithm'
        self.config['pop_size'] = 20
        #self.config['selection_ratio'] = 0.5
        self.config['batch_reset'] = True
        self.config['max_examples'] = 10
        self.examples = []  # list of (fitness, patch_str), sorted ascending — mirrors LLMAlgorithm

    def reset(self):
        super().reset()
        self.stats['gen'] = 0
        self.stats['eval_success'] = 0
        self.stats['eval_compile'] = 0
        self.stats['llm_patches_requested'] = 0
        self.stats['llm_missing_patches'] = 0
        self.stats['llm_malformed_patches'] = 0
        self.examples = []

    def setup(self, config):
        super().setup(config)
        sec = config['search.eda']
        self.llm_model = sec['llm_model']
        self.llm_ip = sec['llm_ip']
        self.config['pop_size'] = int(sec['pop_size'])
        self.config['max_examples'] = int(sec.get('max_examples', fallback='10'))
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
            selected_patches = self.select(runs_pop)  # see todo note in self.select()
            distribution = self.estimate_distribution(selected_patches)

            #run search loop
            while not self.stopping_condition(): #default based on #steps (that is, #evaluations) and time
                self.hook_main_loop()
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
                selected_patches = self.select(runs_pop)  # see todo note in self.select()
                distribution = self.estimate_distribution(selected_patches)

            self.hook_search_time(start)
        except KeyboardInterrupt:
            self.report['stop'] = 'keyboard interrupt'
        finally:
            self.hook_vt_vc()
            self.hook_final_distribution(distribution)
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
        filtered = {sol for sol in pop if pop[sol].status == 'SUCCESS'}
        selected = sorted(filtered, key=lambda sol: pop[sol].fitness)

        if not selected:
            raise ValueError(
                "Ninguna solución fue exitosa. Se inicializará una nueva población aleatoria.")
            return select(self.initialize_population)

        return selected

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



    """
    Samples a population of patches based on the received univariate distribution of single edits, coming from successful patches.
    When a sampled solution (of 1 edit) already exists, it is merged with another randomly sampled edit (+1 edit).
    Thus, repeated patches are avoided, but frequent successful edits are sampled and merged with new edits (via mutate method)
    
    @param edits_prob: The distribution received contains the marginal probabilities of each edit 
    which belonged to a SUCCESSFUL solution (patch). Note an edit is not only a type of edit, but also
    the target and ingredient of the edit. 
    
    @param elitism: If True, make sure that the best patch found in all past generations is included in the new population.
     
    """


    def sample_population(self, edits_prob, elitism=False):

        population = []

        # if elitism is True, keep the best patch found so far
        i=0
        if elitism and self.report.get('best_patch'):
            best_patch = copy.deepcopy(self.report['best_patch'])
            population.append(best_patch)
            i=1

        if self.llm_model == 'None': #sample from distribution
            for _ in range(i, int(self.config['pop_size'])):
                # create solution (patch) with 1 randomly sampled edit
                edit_str = random.choices(list(edits_prob.keys()), weights=list(edits_prob.values()))[0]
                edit = self._edit_from_str(edit_str)
                sol = magpie.core.Patch()
                sol.edits.append(edit)
                # if solution exists in new pop, add random edit (now solution has 2 edits)
                if self.isIn(sol, population):
                    self.mutate(sol)
                population.append(sol)

        else: #use llm to sample patches
            patches_list, explanations_list = self.llm_sample_population(edits_prob, int(self.config['pop_size']) - i)
            for patch_str, explain_str in zip(patches_list, explanations_list):
                # patch may contain one or several edits separated by |
                edit_str_list = [e.strip() for e in patch_str.split('|') if e.strip()]
                sol = magpie.core.Patch()
                try:
                    for edit_str in edit_str_list:
                        edit = self._edit_from_str(edit_str)
                        sol.edits.append(edit)
                    #if variant cannot be created, some patch in sol in wrong and thus ValueError is thrown
                    magpie.core.Variant(self.software, sol)
                except (RuntimeError, ValueError, AssertionError, Exception):
                    self.software.logger.error(f"Error parsing edit from llm. Random 1-edit individual created.")
                    self.stats['llm_malformed_patches'] += 1
                    sol = magpie.core.Patch()
                    self.mutate(sol)
                    explain_str = "invalid creation by LLM, random 1-edit individual created"
                if self.isIn(sol, population):
                    self.mutate(sol)
                population.append(sol)
        return population

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
            explanations.append('LLM returned too few patches, random fallback')
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

    def _llm_call(self,prompt):
        url = f"http://{self.llm_ip}:11434/api/generate"
        payload = {
            "model": f"{self.llm_model}",
            "prompt": f"{prompt}",
            "stream": False,
            "options": {"num_ctx": 32768}
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()["response"]



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
        for edit, prob in distribution.items():
            msg += f'  {edit}: {prob:.4f}\n'
        msg += f'[search.umda] Total edits from successful patches: {len(distribution)}'
        self.software.logger.info(msg)

    def hook_llm_format_stats(self):
        if self.llm_model in (None, 'None'):
            return
        requested = self.stats.get('llm_patches_requested', 0)
        missing = self.stats.get('llm_missing_patches', 0)
        malformed = self.stats.get('llm_malformed_patches', 0)
        ratio_missing = (missing / requested) if requested else 0.0
        ratio_malformed = (malformed / requested) if requested else 0.0
        self.software.logger.info(
            f'[search.eda] LLM malformed patches: {malformed}/{requested} ({ratio_malformed:.3f}), '
            f'missing patches: {missing}/{requested} ({ratio_missing:.3f})'
        )


magpie.utils.known_algos.append(UMDAAlgorithm)