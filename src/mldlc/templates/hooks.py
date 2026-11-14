"""Connect the spec to this project's code. Every function is optional.

model_inputs()     what the code really uses; G1 compares it with the spec's model-inputs block.
serving_columns()  the columns the serving payload accepts; it must equal the model inputs, so a column that
                   is only known after the event is rejected instead of leaking into predictions.
smoke_payload()    a valid pandas DataFrame the release check scores, to prove the registered model can serve.
"""


def model_inputs() -> dict:
    return {"target": "TODO", "features": ["TODO"]}


def serving_columns() -> list[str]:
    return model_inputs()["features"]


def smoke_payload():
    raise NotImplementedError("return a small DataFrame of valid model inputs")
