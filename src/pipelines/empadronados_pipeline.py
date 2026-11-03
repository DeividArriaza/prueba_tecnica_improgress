from src.pipelines.factory import build_pipeline


def build_empadronados_pipeline(fecha):
    return build_pipeline("empadronados", fecha)
