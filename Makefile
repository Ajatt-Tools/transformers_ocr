PROG = transformers_ocr
LISTENER = listener.py
SHORT_PROG = trocr
PREFIX ?= /usr

.PHONY: all
all:
	@echo -e "\033[1;32mThis program doesn't need to be built. Run \"make install\".\033[0m"

.PHONY: install
install:
	@echo -e '\033[1;32mInstalling the program...\033[0m'
	install -Dm644 src/$(LISTENER) -t "$(PREFIX)/lib/$(PROG)/"
	install -Dm755 src/$(PROG).sh "$(PREFIX)/bin/$(PROG)"
	ln -srf -- "$(PREFIX)/bin/$(PROG)" "$(PREFIX)/bin/$(SHORT_PROG)"

.PHONY: uninstall
uninstall:
	@echo -e '\033[1;32mUninstalling the program...\033[0m'
	rm -- "$(PREFIX)/bin/$(PROG)" "$(PREFIX)/bin/$(SHORT_PROG)"
	rm -rf -- "$(PREFIX)/lib/$(PROG)"

.PHONY: clean
clean:
	@echo -e '\033[1;32mCleaning up...\033[0m'
	rm -rf -- "$(PROG)"
