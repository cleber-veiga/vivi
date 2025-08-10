url_videos_disponiveis = {
    "pix_carrinho": {
        "description": """Mostra a finalização de uma venda através do carrinho de vendas. Use sempre que o usuário tiver interesse em saber
mais sobre o funcionamento das vendas no sistema, principalmente em situações que necessitar rapidez. Neste caso enfatize que o usuário pode
utilizar o pix em segundo plano, gerando o QrCode para pix diretamente no carrinho e depois seguir suas vendas normalmente, ficando o sistema
responsável por verificar a efetividade do acerto financeiro junto a instituição financeira, e posteriormente aprovando a venda de maneira automática..
Isso reduz filas e trás mais autonomia aos vendedores
""",
        "url": "https://storage.googleapis.com/vivi-dev-bucket/video/Pix_carrinho.mp4"
    },
    "baixa_duplicata_receber": {
        "description": """Mostra o processo de baixa de duplicata a receber. Use sempre que o usuário ter curiosidades sobre o processo financeiro
Ressalte que na mesma tela além das baixas o usuário pode fazer alterações de onde irá receber, como irá receber e também cálcular e aplicar juros
""",
        "url": "https://storage.googleapis.com/vivi-dev-bucket/video/Baixa_Duplicata_Receber.mp4"
    },
    "carrinho_finaliza": {
        "description": """Mostra a finalização de uma venda através do carrinho de vendas. Use sempre que o usuário tiver interesse em saber
mais sobre o funcionamento das vendas no sistema, principalmente em situações que necessitar rapidez. Neste caso o carrinho está sendo 
finalizado na forma de pagamento boleto
""",
        "url": "https://storage.googleapis.com/vivi-dev-bucket/video/Carringo_Finalizando_Boleto.mp4"
    },
    "entrega_expedicao": {
        "description": """Mostra como funciona o processo de alocação de carga no sistema até a entrega da mercadoria. Enfatize a praticidade da tela permitindo
na mesma tela o usuário ver a cargas pendentes, notas pendentes, produtos das notas. Isso traz agilidade no processo de 
expedição de mercadorias
""",
        "url": "https://storage.googleapis.com/vivi-dev-bucket/video/Entrega_Expedicao.mp4"
    },
    "pix_caixa": {
        "description": """Mostra o processo do caixa da empresa, finalizando uma venda em pix. Ressalte a importância de ter integrações no processo de venda pelo caixa e 
e também a facilidade que a rotina traz para os usuários""",
        "url": "https://storage.googleapis.com/vivi-dev-bucket/video/Finaliza_Caixa_Pix.mp4"
    },
    "roteirizador": {
        "description": """Mostra o processo de definição de rotas no construshow com uso do Roteirizador, que integra diretamente
com o mapas possibilitando visualizar, calcular rotas, definir pontos iniciais e finais, além de permitir visualizar os locais onde 
as entregas serão feitas. Ressalte a importância disso quando enviar o vídeo""",
        "url": "https://storage.googleapis.com/vivi-dev-bucket/video/roteirizador.mp4"
    }
}


def get_url_videos_disponíveis():
    return url_videos_disponiveis


def get_url_video_by_id(video_id: str) -> str:
    video_data = url_videos_disponiveis.get(video_id)
    if not video_data:
        return None  # ou lançar uma exceção se preferir
    return video_data.get("url")