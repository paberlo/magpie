import copy
import random
import re
import time

import magpie.core
import magpie.utils
import requests


class LLMAlgorithm(magpie.core.BasicAlgorithm):
    def __init__(self):
        super().__init__()
        self.name = 'LLM Algorithm'
        self.config['pop_size'] = 20
        self.config['batch_reset'] = True
        self.config['max_examples'] = 10
        self.examples = []  # list of (fitness, patch_str), sorted ascending by fitness

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
        sec = config['search.llm']
        self.llm_model = sec['llm_model']
        self.llm_ip = sec['llm_ip']
        self.config['pop_size'] = int(sec['pop_size'])
        self.config['max_examples'] = int(sec.get('max_examples', fallback='10'))
        tmp = sec.get('batch_reset', fallback='true').lower()
        if tmp in ['true', 't', '1']:
            self.config['batch_reset'] = True
        elif tmp in ['false', 'f', '0']:
            self.config['batch_reset'] = False
        else:
            msg = '[search.llm] batch_reset should be Boolean'
            raise magpie.core.ScenarioError(msg)

    def run(self):
        try:
            self.hook_warmup()
            patches_population = self.initialize_population()
            self.warmup()
            if self.report['stop']:
                return
            self.hook_start()

            start = time.perf_counter()

            # eval initial population
            runs_pop = {}
            generation_best_fitness = None
            for patch in patches_population:
                variant = magpie.core.Variant(self.software, patch)
                run = self.evaluate_variant(variant)
                self.update_vt_vc(run)
                accept, best, generation_best_fitness = self.updateBest(run, generation_best_fitness, patch)
                self.hook_evaluation(variant, run, accept, best)
                runs_pop[patch] = run
                self.stats['steps'] += 1

            self._update_examples(runs_pop)

            while not self.stopping_condition():
                self.hook_main_loop()
                patches_population = self.sample_population(elitism=True)

                generation_best_fitness = None
                runs_pop.clear()

                for sol in patches_population:
                    if self.stopping_condition():
                        break
                    variant = magpie.core.Variant(self.software, sol)
                    run = self.evaluate_variant(variant)
                    self.update_vt_vc(run)
                    accept, best, generation_best_fitness = self.updateBest(run, generation_best_fitness, sol)
                    self.hook_evaluation(variant, run, accept, best)
                    runs_pop[sol] = run
                    self.stats['steps'] += 1

                self._update_examples(runs_pop)

            self.hook_search_time(start)
        except KeyboardInterrupt:
            self.report['stop'] = 'keyboard interrupt'
        finally:
            self.hook_vt_vc()
            self.hook_final_examples()
            self.hook_llm_format_stats()
            self._hook_explanation_best_patch()
            self.hook_end()

    def updateBest(self, run, local_best_fitness, sol):
        accept = best = False
        if run.status == 'SUCCESS':
            if self.dominates(run.fitness, local_best_fitness):
                local_best_fitness = run.fitness
                accept = True
                if self.dominates(run.fitness, self.report['best_fitness']):
                    self.report['best_fitness'] = run.fitness
                    self.report['best_patch'] = sol
                    best = True
        return accept, best, local_best_fitness

    def aux_log_counter(self):
        gen = self.stats['gen']
        step = self.stats['steps'] % self.config['pop_size'] + 1
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

    def sample_population(self, elitism=False):
        population = []
        i = 0
        if elitism and self.report.get('best_patch'):
            best_patch = copy.deepcopy(self.report['best_patch'])
            population.append(best_patch)
            i = 1

        n = int(self.config['pop_size']) - i
        patches_list, explanations_list = self.llm_sample_population(n)
        for patch_str, explain_str in zip(patches_list, explanations_list):
            edit_str_list = [e.strip() for e in patch_str.split('|') if e.strip()]
            sol = magpie.core.Patch()
            try:
                for edit_str in edit_str_list:
                    edit = self._edit_from_str(edit_str)
                    sol.edits.append(edit)
                magpie.core.Variant(self.software, sol)
            except (RuntimeError, ValueError, AssertionError, Exception):
                self.software.logger.error('Error parsing edit from LLM. Random 1-edit individual created.')
                self.stats['llm_malformed_patches'] += 1
                sol = magpie.core.Patch()
                self.mutate(sol)
            if self.isIn(sol, population):
                self.mutate(sol)
            population.append(sol)
        return population

    def llm_sample_population(self, pop_size):
        prompt = self._craft_population_prompt(pop_size)
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

    def _craft_population_prompt(self, pop_size):
        sw_srcmodel = next(iter(self.software.noop_variant.models.items()))[1]
        sw_text = sw_srcmodel.dump()

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

        prompt = (
            f'In the context of Genetic Improvement of software, I want to create {pop_size} new Patches '
            f'for the following original software.\n\n'
            f'Each patch contains 1 or more edits in the MAGPIE framework format '
            f'(XmlNodeDeletion, XmlNodeReplacement, or XmlNodeInsertion). '
            f'Multiple edits in a patch are separated by "|".\n\n'
            f'The fitness goal is to reduce the execution time of the original software.\n\n'
            f'This is the original software:\n{sw_text}\n\n'
            f'{examples_block}\n'
            f'Respect the required format, only reply with a numbered set of {pop_size} patch+explanation, '
            f'no further extra text. For instance:\n'
            f'Patch 1: XmlNodeDeletion<stmt>((\'file.xml\', \'stmt\', 3))\n'
            f'Explanation 1: Removes an unnecessary statement to reduce execution time.\n'
            f'Patch 2: XmlNodeDeletion<stmt>((\'file.xml\', \'stmt\', 5)) | '
            f'XmlNodeInsertion<stmt,block>((\'file.xml\', \'_inter_block\', 2), (\'file.xml\', \'stmt\', 1))\n'
            f'Explanation 2: Combines a deletion with an insertion to restructure a hot path.\n'
        )
        return prompt

    def _llm_call(self, prompt):
        url = f'http://{self.llm_ip}:11434/api/generate'
        payload = {
            'model': self.llm_model,
            'prompt': prompt,
            'stream': False,
            'options': {'num_ctx': 32768},
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()['response']

    def _filter_llm_patches_and_explainations(self, response_str):
        matches = re.findall(
            r'^\s*(?:\d+\.\s*)?Patch\s*\d*:\s*(.+?)\s*[\r\n]+'
            r'\s*Explanation\s*\d*:\s*(.+?)(?=\s*[\r\n]+\s*(?:\d+\.\s*)?Patch\s*\d*:|\Z)',
            response_str,
            re.MULTILINE | re.DOTALL,
        )
        patches = [p.strip() for p, _ in matches]
        explanations = [e.strip() for _, e in matches]
        return patches, explanations

    def _edit_from_str(self, edit_str):
        target = magpie.utils.convert.target_from_stringEdit(edit_str)
        ingredient = magpie.utils.convert.ingredient_from_stringEdit(edit_str)
        if '<' in edit_str:
            edit_str = edit_str.split('>')[0] + '>'
        else:
            edit_str = edit_str.split('(')[0]
        klass = magpie.utils.edit_from_string(edit_str)
        edit = klass.auto_create(self.software.noop_variant)
        edit.target = target
        if ingredient:
            edit.data = [ingredient]
        return edit

    def isIn(self, sol, population):
        for p in population:
            if str(sol) == str(p):
                return True
        return False

    def hook_main_loop(self):
        self.stats['gen'] += 1
        if self.config['batch_reset']:
            for a in self.config.get('batch_bins', []):
                random.shuffle(a)
            self.hook_reset_batch()

    def hook_search_time(self, start):
        end = time.perf_counter()
        msg = f'[search.llm] Search time: {end - start:.3f} seconds'
        self.software.logger.info(msg)

    def _hook_explanation_best_patch(self):
        if self.report['best_patch'] is not None:
            patch_str = self.report['best_patch']
            try:
                explain_str = self._llm_explain_patch(patch_str)
            except Exception:
                explain_str = 'Ollama service failed, no explanation available'
            self.software.logger.info('LLM Explanation of best patch: ' + explain_str)

    def _llm_explain_patch(self, patch_str):
        sw_srcmodel = next(iter(self.software.noop_variant.models.items()))[1]
        sw_str = sw_srcmodel.dump()
        prompt = (
            f'Give a very brief explanation of the potential benefit in execution time of the following patch: {patch_str}\n'
            f'in the following code:\n{sw_str}.\n'
            f'3-5 lines only. Do not explain the patch format, just the potential performance benefit.'
        )
        return self._llm_call(prompt)

    def hook_final_examples(self):
        msg = '[search.llm] Final examples (best patches found):\n'
        for i, (fitness, patch_str) in enumerate(self.examples):
            msg += f'  {i+1}. {patch_str}  (fitness: {fitness})\n'
        self.software.logger.info(msg)

    def hook_llm_format_stats(self):
        requested = self.stats.get('llm_patches_requested', 0)
        missing = self.stats.get('llm_missing_patches', 0)
        malformed = self.stats.get('llm_malformed_patches', 0)
        ratio_missing = (missing / requested) if requested else 0.0
        ratio_malformed = (malformed / requested) if requested else 0.0
        self.software.logger.info(
            f'[search.llm] LLM malformed patches: {malformed}/{requested} ({ratio_malformed:.3f}), '
            f'missing patches: {missing}/{requested} ({ratio_missing:.3f})'
        )


magpie.utils.known_algos.append(LLMAlgorithm)
