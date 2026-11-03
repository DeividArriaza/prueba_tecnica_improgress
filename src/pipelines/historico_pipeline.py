from src.pipelines.factory import build_pipeline


def build_centros_pipeline():
    return build_pipeline("centros_votacion")


def build_resultados_pipeline():
    return build_pipeline("resultados_historicos")
