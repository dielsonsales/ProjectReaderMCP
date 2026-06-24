.PHONY: test

test:
	python -m pytest tests/test_server.py tests/utils/test_file_utils.py
