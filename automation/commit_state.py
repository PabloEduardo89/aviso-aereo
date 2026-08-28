"""
Comita e empurra automation/state/posted.json de volta pro repositório —
chamado pelo passo final do workflow (.github/workflows/post-avisos.yml),
depois de "Rodar ciclo de publicação".

Usa o mesmo helper resiliente a push concorrente que publish.py usa pra
hospedar as imagens dos posts (ver git_utils.py) — antes esse passo era um
`git push` cru direto no YAML, sem retry nenhum, e foi o que fez a execução
inteira falhar em 2026-08-26 quando outro push concorrente (de qualquer
origem) chegou no meio do ciclo.
"""
import os
import sys

from git_utils import commit_and_push

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    changed = commit_and_push(
        REPO_ROOT,
        ["automation/state/posted.json", "automation/state/last_post_format.json"],
        "state: atualiza registro de posts [skip ci]",
    )
    print("Estado atualizado e enviado." if changed else "Nada novo pra comitar.")
