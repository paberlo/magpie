import abc
import copy
import random

import magpie.core
import magpie.utils

import time

class UMDAAlgorithm(magpie.core.BasicAlgorithm):
    def __init__(self):
        super().__init__()
        self.name = 'UMDA Algorithm'
        self.config['pop_size'] = 20
        #self.config['selection_ratio'] = 0.5
        self.config['batch_reset'] = True

    def reset(self):
        super().reset()
        self.stats['gen'] = 0
        self.stats['eval_success'] = 0
        self.stats['eval_compile_error'] = 0

    def setup(self, config):
        super().setup(config)
        sec = config['search.eda']
        self.config['pop_size'] = int(sec['pop_size'])
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

                if run.status == 'SUCCESS': #counter to log success proportion
                    self.stats['eval_success'] += 1
                if isinstance(run.status, str) and run.status.startswith('COMPILE_'):
                    self.stats['eval_compile_error'] += 1

                accept, best, generation_best_fitness = self.updateBest(run, generation_best_fitness, patch)
                self.hook_evaluation(variant, run, accept, best)
                runs_pop[patch] = run
                self.stats['steps'] += 1 #steps son validaciones, max_steps en secenario indica numero maximo de evaluciones.

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
                    variant = magpie.core.Variant(self.software, sol)
                    run = self.evaluate_variant(variant)

                    if run.status == 'SUCCESS':
                        self.stats['eval_success'] += 1
                    if isinstance(run.status, str) and run.status.startswith('COMPILE_'):
                        self.stats['eval_compile_error'] += 1

                    accept, best, generation_best_fitness = self.updateBest(run, generation_best_fitness, sol)
                    self.hook_evaluation(variant, run, accept, best)
                    runs_pop[sol] = run
                    self.stats['steps'] += 1

                selected_patches = self.select(runs_pop)  # see todo note in self.select()
                distribution = self.estimate_distribution(selected_patches)

            self.hook_search_time(start)
        except KeyboardInterrupt:
            self.report['stop'] = 'keyboard interrupt'
        finally:
            total =self.stats['steps']
            succ = self.stats.get('eval_success', 0)
            comp = self.stats.get('eval_compile_error', 0)

            ratio_succ = (succ / total) if total else 0.0
            ratio_comp = (comp / total) if total else 0.0

            self.software.logger.info(
                f'[search.umda] Overall SUCCESS ratio {ratio_succ:.3f} ({succ}/{total})'
            )
            self.software.logger.info(
                f'[search.umda] Overall COMPILE_ERROR ratio {ratio_comp:.3f} ({comp}/{total})'
            )

            self.hook_final_distribution(distribution)
            self.hook_end()

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

        for _ in range(i, int(self.config['pop_size'])):

            # create solution (patch) with 1 randomly sampled edit
            edit = self._sample_edit(edits_prob)
            sol = magpie.core.Patch()
            sol.edits.append(edit)

            # if solution exists in new pop, add random edit (now solution has 2 edits)
            if self.isIn(sol, population):
                self.mutate(sol)

            population.append(sol)

        return population

    def isIn(self, sol, population):
        for p in population:
            if str(sol) == str(p): #__eq__ of abstract_edit has problems with equality of classes under WSL environment
                return True
        return False

    def _sample_edit(self,edits_prob):
        edit_str = random.choices(list(edits_prob.keys()), weights=list(edits_prob.values()))[0]
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


magpie.utils.known_algos.append(TabuSearch)