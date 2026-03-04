from app.services.store_search.google_search import GoogleSearcher

# Tek bir Google araması tüm Türk e-ticaret sitelerini kapsar
ALL_SEARCHERS = [
    GoogleSearcher(),
]
