from homeassistant.helpers.template import Template


async def test_compact_card_template(hass):
    hass.states.async_set("sensor.raccolta_rifiuti", "Carta, Verde", {"collection_type_codes": ["paper", "green", "xyz"]})
    tpl = """{% set img = {'paper':'carta','plastic':'plastica','glass':'vetro','organic':'umido',
                  'residual':'indifferenziata','metal':'metallo','green':'verde'} %}
    {% for c in state_attr('sensor.raccolta_rifiuti','collection_type_codes') or [] %}{{ img.get(c, 'default') }}.png {% endfor %}"""
    out = Template(tpl, hass).async_render()
    assert out.split() == ["carta.png", "verde.png", "default.png"]
