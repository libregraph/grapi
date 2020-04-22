# Tools

XGETTEXT ?= xgettext
MSGMERGE ?= msgmerge
MSGFMT ?= msgfmt

# Variables

POS = $(wildcard *.po)

# Translations

.PHONY: extract
extract: pot

.PHONY: pot
pot:
	$(XGETTEXT) \
		-L Python \
		--package-name=GRAPI \
		--package-version= \
		--from-code=UTF-8 \
		--add-comments \
		--force-po \
		--no-location \
		--no-wrap \
		--foreign-user \
		--sort-output \
		--output - \
		$(shell find ../grapi/ -name "*.py") | grep -v '^#' > messages.pot

.PHONY: merge
merge: $(POS)

.PHONY: stats
stats:
	$(foreach po, $(POS), $(shell $(MSGFMT) -v --statistics $(po)))
	@- true

$(POS): FORCE messages.pot
	$(MSGMERGE) -U \
		--backup=none \
		--no-wrap \
		$@ messages.pot

FORCE:
