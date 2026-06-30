CPU := $(shell nproc)

build:
	maturin develop --release

test:
	cargo test --all -- --test-threads=$(CPU)
	pytest -n $(CPU)

lint:
	cargo clippy --all-targets --all-features -- -D warnings
	ruff check python

format:
	cargo fmt
	ruff format python
