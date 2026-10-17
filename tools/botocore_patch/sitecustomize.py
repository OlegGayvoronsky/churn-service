# Убирает заголовок Expect: 100-continue у botocore.
# Нужен, если dvc push через ingress s3.localhost зависает на 60 с и падает с 499.
try:
    import botocore.handlers as _h

    _h.BUILTIN_HANDLERS[:] = [
        item for item in _h.BUILTIN_HANDLERS
        if getattr(item[1], "__name__", "") != "add_expect_header"
    ]
except Exception:
    pass