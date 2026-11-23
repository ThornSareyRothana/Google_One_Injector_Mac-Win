#!/bin/zsh
cd -- "${0:A:h}" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
if [[ ! -x .venv/bin/python ]]; then
    echo "Python environment missing. Run setup first."
    read -r "?Press Return to close."
    exit 1
fi
.venv/bin/python main.py "$@"
result=$?
if (( result != 0 )); then
    echo "Launcher exited with code $result."
    read -r "?Press Return to close."
fi
exit "$result"
