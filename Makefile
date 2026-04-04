.PHONY: lint lint-markdown validate-yaml validate-json validate-shell security-injection release-metadata validate doctor eval eval-all eval-ci eval-skills eval-agents eval-triggers eval-output eval-baseline eval-compare eval-overlap eval-confusable eval-hard-corpus eval-behavioral eval-behavioral-verbose eval-behavioral-fresh eval-behavioral-fresh-verbose eval-behavioral-compare eval-stress eval-tests eval-tests-pytest eval-tests-unittest ci

lint:
	npm run lint

lint-markdown:
	npm run lint:markdown

validate-yaml:
	bash scripts/validate-yaml.sh

validate-json:
	bash scripts/validate-json.sh

validate-shell:
	bash scripts/validate-shell.sh

security-injection:
	bash scripts/check-dynamic-injection.sh

release-metadata:
	python3 scripts/check-release-metadata.py

validate:
	bash scripts/validate-plugin.sh

doctor:
	bash scripts/check-contributor-prereqs.sh

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

eval-output:
	python3 -m lab.eval.artifact_scorer --all

eval-baseline:
	python3 -m lab.eval.baseline

eval-compare: ## Compare eval results (requires: make eval-baseline first)
	python3 -m lab.eval.compare --pretty

eval-overlap:
	python3 -m lab.eval.trigger_scorer --overlap --pretty

eval-confusable:
	python3 -m lab.eval.triggers.generate_confusable_pairs

eval-hard-corpus:
	python3 -m lab.eval.triggers.generate_hard_corpus

eval-behavioral:
	python3 -m lab.eval.behavioral_scorer --all --cache --summary
	python3 -m lab.eval.scorer --all --behavioral --pretty

eval-behavioral-verbose:
	python3 -m lab.eval.behavioral_scorer --all --cache --summary --verbose
	python3 -m lab.eval.scorer --all --behavioral --pretty

eval-behavioral-fresh:
	python3 -m lab.eval.behavioral_scorer --all --summary
	python3 -m lab.eval.scorer --all --behavioral --pretty

eval-behavioral-fresh-verbose:
	python3 -m lab.eval.behavioral_scorer --all --summary --verbose
	python3 -m lab.eval.scorer --all --behavioral --pretty

eval-behavioral-compare:
	python3 -m lab.eval.scorer --compare

eval-stress:
	python3 -m lab.eval.evaluator_stress_test

eval-tests:
	bash scripts/run-eval-tests.sh

eval-tests-pytest:
	python3 -m pytest lab/eval/tests -v

eval-tests-unittest:
	python3 -m unittest discover -s lab/eval/tests -p 'test_*.py' -t . -v

ci: doctor lint release-metadata validate eval-tests eval-ci
