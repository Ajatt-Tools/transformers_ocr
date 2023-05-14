PROG = transformers_ocr
SHORT_PROG = trocr
PREFIX ?= /usr

VPATH = src

EXEC_FILES := $(wildcard $(VPATH)/*.py)

EXEC_INSTALL := $(patsubst $(VPATH)/%.py,$(PREFIX)/bin/%,$(EXEC_FILES))

.PHONY: all
all:
	@echo -e "\033[1;32mThis program doesn't need to be built. Run \"make install\".\033[0m"

$(PREFIX)/bin/%: $(VPATH)/%.py
	install -Dm755 $< $@

$(PREFIX)/bin/$(SHORT_PROG): $(PREFIX)/bin/$(PROG)
	ln -srf -- $< $@

.PHONY: install
install: $(EXEC_INSTALL) $(PREFIX)/bin/$(SHORT_PROG)
	@echo -e '\033[1;32mInstalling the program...\033[0m'

.PHONY: uninstall
uninstall:
	@echo -e '\033[1;32mUninstalling the program...\033[0m'
	rm -- $(PREFIX)/bin/$(SHORT_PROG)
	rm -- $(EXEC_INSTALL)

.PHONY: clean
clean:
	@echo -e '\033[1;32mCleaning up...\033[0m'
	rm -rf -- out
