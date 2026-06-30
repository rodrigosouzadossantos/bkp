# vim: ft=makefile noet ts=4 sw=4 :
# Makefile for building the Project

.DEFAULT_GOAL := help
.PHONY: help all en-web pt-web en-book pt-book clean build

help:
	@echo "AI Project Governance - Build System"
	@echo "------------------------------------"
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  en-web    : Build English Website"
	@echo "  pt-web    : Build Portuguese Website"
	@echo "  en-book   : Build English Book (PDF/HTML)"
	@echo "  pt-book   : Build Portuguese Book (PDF/HTML)"
	@echo "  all       : Build all 4 versions"
	@echo "  clean     : Remove build artifacts"

all: en-web pt-web en-book pt-book

en-web:
	quarto render --profile en,web --output-dir _site/en/web

pt-web:
	quarto render --profile pt,web --output-dir _site/pt/web

en-book:
	quarto render --profile en,book --output-dir _site/en/book

pt-book:
	quarto render --profile pt,book --output-dir _site/pt/book

clean:
	quarto clean

