"""
Commit+push resiliente a push concorrente — usado tanto por publish.py
(hospedar imagem no GitHub, dentro do loop de publicação) quanto pelo passo
final do workflow (comitar automation/state/posted.json, ver commit_state.py).

Existe por causa de um incidente real (2026-08-26, execução 33021086018): um
push concorrente no mesmo branch main (na época, edições no index.html feitas
em paralelo por outra sessão) foi rejeitado (`! [rejected] main -> main
(fetch first)`) porque o `git push` daqui não tentava se atualizar antes de
empurrar de novo — isso abortou a publicação de 1 post e, pior, também
impediu o commit final do state.json de ir pro ar, criando risco de post
duplicado na execução seguinte (dedup baseado num arquivo que não tinha sido
atualizado no repo).

A automação só mexe em posts/<icao>/*.png e automation/state/posted.json —
NUNCA em index.html ou qualquer outro arquivo do app — então um rebase sobre
o que avançou no branch nunca deveria ter conflito de verdade: só precisa "se
atualizar" antes de empurrar. Por isso o retry aqui é simples (fetch + rebase
+ tenta de novo), sem nenhuma lógica de merge complexa.
"""
import subprocess
import time

MAX_RETRIES = 5
RETRY_DELAY_SECONDS = 5


class GitPushError(RuntimeError):
    pass


def commit_and_push(repo_root: str, rel_paths: list, commit_message: str, branch: str = "main") -> bool:
    """git add + commit (só se houver mudança) + push dos `rel_paths` (caminhos
    relativos a `repo_root`). Se o push for rejeitado por non-fast-forward
    (push concorrente de QUALQUER origem, não só do app), faz `git fetch` +
    `git rebase origin/<branch>` e tenta de novo, até MAX_RETRIES vezes, com
    um pequeno intervalo entre tentativas.

    Devolve True se comitou e empurrou algo; False se não havia nenhuma
    mudança em `rel_paths` pra comitar (nada a fazer, não é erro). Levanta
    GitPushError se esgotar as tentativas ou se o rebase encontrar um
    conflito de verdade (nesse caso aborta o rebase antes de levantar, pra
    não deixar o checkout do runner num estado quebrado)."""
    subprocess.run(["git", "-C", repo_root, "add", *rel_paths], check=True)
    status = subprocess.run(["git", "-C", repo_root, "status", "--porcelain", *rel_paths],
                             capture_output=True, text=True, check=True)
    if not status.stdout.strip():
        return False

    subprocess.run(["git", "-C", repo_root, "commit", "-m", commit_message], check=True)

    for attempt in range(1, MAX_RETRIES + 1):
        push = subprocess.run(["git", "-C", repo_root, "push", "origin", branch],
                               capture_output=True, text=True)
        if push.returncode == 0:
            return True

        print(f"[git_utils] push rejeitado (tentativa {attempt}/{MAX_RETRIES}): "
              f"{push.stderr.strip()[:300]}")
        if attempt == MAX_RETRIES:
            raise GitPushError(f"git push falhou após {MAX_RETRIES} tentativas: {push.stderr.strip()}")

        subprocess.run(["git", "-C", repo_root, "fetch", "origin", branch], check=True)
        rebase = subprocess.run(["git", "-C", repo_root, "rebase", f"origin/{branch}"],
                                 capture_output=True, text=True)
        if rebase.returncode != 0:
            # conflito de verdade (inesperado — a automação não mexe nos mesmos
            # arquivos que mais nada no repo) — aborta o rebase em vez de deixar
            # o checkout do runner num estado pela metade, e desiste com erro claro
            subprocess.run(["git", "-C", repo_root, "rebase", "--abort"], check=False)
            raise GitPushError(f"git rebase encontrou conflito real: {rebase.stderr.strip()}")

        time.sleep(RETRY_DELAY_SECONDS)

    return True  # inalcançável — o loop acima sempre retorna ou levanta antes
