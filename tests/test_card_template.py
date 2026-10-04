from homeassistant.helpers.template import Template


async def test_compact_card_template(hass):
    hass.states.async_set("sensor.raccolta_rifiuti", "Carta, Verde", {"collection_type_codes": ["paper", "green", "xyz"]})
    tpl = """{% set img = {'paper':'carta','plastic':'plastica','glass':'vetro','organic':'umido',
                  'residual':'indifferenziata','metal':'metallo','green':'verde'} %}
    {% for c in state_attr('sensor.raccolta_rifiuti','collection_type_codes') or [] %}{{ img.get(c, 'default') }}.png {% endfor %}"""
    out = Template(tpl, hass).async_render()
    assert out.split() == ["carta.png", "verde.png", "default.png"]


async def test_lovelace_example_markdown(hass):
    import pathlib

    from homeassistant.util.yaml import load_yaml

    view = load_yaml(pathlib.Path(__file__).resolve().parents[1] / "examples/lovelace_raccolta.yaml")
    md = view["sections"][0]["cards"][1]["content"]
    hass.states.async_set("sensor.raccolta_differenziata_domani", "x", {"collection_type_codes": ["organic", "paper"], "message": "Umido e Carta"})
    out = Template(md, hass).async_render()
    assert "umido.png" in out and "carta.png" in out and "Umido e Carta" in out
    hass.states.async_set("sensor.raccolta_differenziata_domani", "x", {"collection_type_codes": []})
    hass.states.async_set("sensor.raccolta_differenziata_prossima_raccolta", "2026-10-09", {"next_collection_types": ["Indifferenziata", "Umido"]})
    out = Template(md, hass).async_render()
    assert "09/10" in out and "Indifferenziata, Umido" in out
