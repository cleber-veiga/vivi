from pathlib import Path

def find_project_root(root_name="app") -> Path:
    """
    Sobe a partir do arquivo atual até encontrar um diretório chamado `root_name`.
    """
    current = Path(__file__).resolve()
    print(f"[find_root] __file__ resolve: {current}")
    for parent in current.parents:
        print(f"[find_root] subindo para: {parent}")
        if parent.name == root_name:
            print(f"[find_root] encontrou raiz '{root_name}' em: {parent}")
            return parent
    raise RuntimeError(f"Não achei a pasta raiz chamada '{root_name}'")