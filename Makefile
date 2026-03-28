.PHONY: lint security-injection eval eval-all eval-ci eval-skills eval-agents eval-triggers eval-baseline eval-compare eval-overlap eval-confusable eval-hard-corpus eval-stress eval-tests eval-tests-pytest eval-tests-unittest ci

lint:
	npm run lint

security-injection:
	bash scripts/check-dynamic-injection.sh

eval:
	bash lab/eval/run_eval.sh --changed

eval-all:
	bash lab/eval/run_eval.sh --all

eval-ci:
	bash lab/eval/run_eval.sh --ci

eval-skills:
	bash lab/eval/run_eval.sh --skills

eval-agents:
	bash lab/eval/run_eval.sh --agents

eval-triggers:
	bash lab/eval/run_eval.sh --triggers

eval-baseline:
	python3 -m lab.eval.baseline

eval-compare:
	python3 -m lab.eval.compare --pretty

eval-overlap:
	python3 -m lab.eval.trigger_scorer --overlap --pretty

eval-confusable:
	python3 -m lab.eval.triggers.generate_confusable_pairs

eval-hard-corpus:
	python3 -m lab.eval.triggers.generate_hard_corpus

eval-stress:
	python3 -m lab.eval.evaluator_stress_test

eval-tests:
	bash scripts/run-eval-tests.sh

eval-tests-pytest:
	python3 -m pytest lab/eval/tests -v

eval-tests-unittest:
	python3 -m unittest discover -s lab/eval/tests -p 'test_*.py' -v

ci: eval-tests eval-ci
