

def test_un_model_que_pensa_te_lloc_per_contestar(monkeypatch):
    """`deepseek-flash` pensa abans de contestar, i el que pensa es cobra del mateix sostre. Amb
    max_tokens=1500 es gastava les 1.499 fitxes pensant i tornava el text buit: producció deia
    «DeepSeek returned empty text» a cada lliçó. Un model que pensa rep sostre de sobres."""
    import deepseek_client as ds
    vist = {}

    class R:  # noqa
        status_code = 200

        @staticmethod
        def json():
            return {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}

    def fake_post(url, **kw):
        vist.update(kw["json"])
        return R()

    monkeypatch.setenv("DEEPSEEK_API_KEY", "x")
    monkeypatch.setattr(ds.requests, "post", fake_post)

    ds.deepseek_generate("s", [{"role": "user", "text": "t"}], max_output_tokens=300,
                         model="deepseek-flash")
    assert vist["max_tokens"] >= ds.THINKER_FLOOR, "el que pensa necessita lloc per contestar"

    ds.deepseek_generate("s", [{"role": "user", "text": "t"}], max_output_tokens=300,
                         model="deepseek-chat")
    assert vist["max_tokens"] == 300, "el de xat no, i no es paga de més"


def test_quan_no_contesta_diu_per_que(monkeypatch):
    """Dir «no ha contestat» no serveix de res: cal dir que s'ha begut el sostre pensant."""
    import deepseek_client as ds

    class R:  # noqa
        status_code = 200

        @staticmethod
        def json():
            return {"choices": [{"message": {"content": ""}, "finish_reason": "length"}],
                    "usage": {"completion_tokens_details": {"reasoning_tokens": 1499}}}

    monkeypatch.setenv("DEEPSEEK_API_KEY", "x")
    monkeypatch.setattr(ds.requests, "post", lambda url, **kw: R())
    try:
        ds.deepseek_generate("s", [{"role": "user", "text": "t"}], model="deepseek-chat")
    except RuntimeError as e:
        assert "1499" in str(e) and "pensant" in str(e), str(e)
    else:
        raise AssertionError("hauria d'haver petat")
