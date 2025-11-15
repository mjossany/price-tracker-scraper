build-PriceTrackerScraperFunction:
	pip install -r requirements-dev.txt -t "$(ARTIFACTS_DIR)" \
		--platform manylinux2014_x86_64 \
		--only-binary=:all: \
		--python-version 3.12 \
		--implementation cp
	cp -r scrapers "$(ARTIFACTS_DIR)"
	cp -r utils "$(ARTIFACTS_DIR)"
	cp lambda_function.py "$(ARTIFACTS_DIR)"
	cp lambda_function_debug.py "$(ARTIFACTS_DIR)"

