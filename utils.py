def get_suivi_map(quotes):
    suivi_map = {}
    for quote in quotes:
        suivi_map[quote.id] = getattr(quote, 'statut_suivi', 'inconnu')  # adapte si nécessaire
    return suivi_map
