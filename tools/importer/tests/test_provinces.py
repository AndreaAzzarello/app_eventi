"""Riquadri delle province: parsing Overpass, regole di build_provinces e controlli su provinces.json."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from build_provinces import build, parse_istat_names, parse_overpass, parse_overpass_names  # noqa: E402
from geo import PROVINCES, in_viewbox  # noqa: E402

OVERPASS = {"elements": [
    {"tags": {"ISO3166-2": "IT-MO", "name": "Modena"}, "bounds": {"minlat": 44.1, "minlon": 10.4, "maxlat": 44.9, "maxlon": 11.4}},
    {"tags": {"ISO3166-2": "IT-23"}, "bounds": {"minlat": 45.4, "minlon": 6.8, "maxlat": 46.0, "maxlon": 7.9}},
    {"tags": {"ISO3166-2": "IT-XX"}},  # senza bounds: ignorata
]}
ISTAT = ("Codice Regione;Codice Comune formato alfanumerico;Denominazione in italiano;"
         "\"Denominazione dell'Unità territoriale sovracomunale \n(valida a fini statistici)\";Denominazione Regione;"
         "Sigla automobilistica\n"
         "08;036023;Modena;Modena;Emilia-Romagna;MO\n"
         "08;035033;Reggio nell'Emilia;Reggio nell'Emilia;Emilia-Romagna;RE\n"
         "02;007003;Aosta;Valle d'Aosta/Vallée d'Aoste;Valle d'Aosta/Vallée d'Aoste;AO\n"
         "03;015146;Milano;Milano;Lombardia;MI\n")


def test_parse_overpass_margine_e_aosta():
    boxes = parse_overpass(OVERPASS, margin=0.05)
    assert boxes == {"MO": "10.350,44.950,11.450,44.050", "AO": "6.750,46.050,7.950,45.350"}


def test_build_nomi_istat_nome_storico_e_mancanti():
    provinces, missing = build(parse_overpass(OVERPASS), parse_istat_names(ISTAT))
    assert provinces["MO"][0] == "Modena" and provinces["AO"][0] == "Valle d'Aosta"
    assert missing == ["MI", "RE"]  # niente confine in OSM: segnalate, non inventate
    names = {**parse_istat_names(ISTAT)}
    assert build({"RE": "1,2,3,4"}, names)[0]["RE"][0] == "Reggio Emilia"  # nome già usato nella geocache


def test_province_italiane_complete_e_riquadri_validi():
    assert len(PROVINCES) >= 100
    for code, (name, box) in PROVINCES.items():
        lon_min, lat_max, lon_max, lat_min = (float(x) for x in box.split(","))
        assert name and lon_min < lon_max and lat_min < lat_max, code
        assert 6 < lon_min and lon_max < 19 and 35 < lat_min and lat_max < 48, code


def test_capoluoghi_dentro_il_loro_riquadro():
    capoluoghi = {"PC": (45.052, 9.693), "PR": (44.801, 10.328), "RE": (44.698, 10.630), "MO": (44.647, 10.925),
                  "BO": (44.495, 11.343), "FE": (44.838, 11.619), "RA": (44.418, 12.203), "FC": (44.222, 12.041),
                  "RN": (44.060, 12.566), "MI": (45.464, 9.190), "BG": (45.698, 9.677), "VE": (45.438, 12.327),
                  "VR": (45.438, 10.992), "FI": (43.769, 11.256), "PI": (43.716, 10.402), "RM": (41.903, 12.496),
                  "AO": (45.737, 7.320), "BZ": (46.498, 11.355), "CA": (39.223, 9.121), "PA": (38.116, 13.361)}
    for code, (lat, lng) in capoluoghi.items():
        assert in_viewbox(lat, lng, PROVINCES[code][1]), code


def test_nomi_emilia_romagna_invariati():
    # geocache.json usa questi nomi nelle chiavi ("via x, modena"): non cambiarli
    assert [PROVINCES[c][0] for c in ("PC", "PR", "RE", "MO", "BO", "FE", "RA", "FC", "RN")] == [
        "Piacenza", "Parma", "Reggio Emilia", "Modena", "Bologna", "Ferrara", "Ravenna", "Forlì-Cesena", "Rimini"]


def test_province_sarde_della_riforma_con_nome_osm():
    osm = {"elements": [
        {"tags": {"ISO3166-2": "IT-OT", "name": "Gallura Nord-Est Sardegna"}, "bounds": {"minlat": 40.5, "minlon": 8.8, "maxlat": 41.3, "maxlon": 9.8}},
        {"tags": {"ISO3166-2": "IT-SS", "name": "Tèttari/Sassari"}, "bounds": {"minlat": 40.3, "minlon": 8.1, "maxlat": 41.1, "maxlon": 9.3}},
    ]}
    assert parse_overpass_names(osm) == {"OT": "Gallura Nord-Est Sardegna"}  # SS c'è nell'ISTAT: nome ISTAT
    provinces, _ = build(parse_overpass(osm), parse_overpass_names(osm))
    assert provinces["OT"][0] == "Gallura Nord-Est Sardegna" and "SS" not in provinces


def test_province_sarde_in_provinces_json():
    for code in ("OT", "OG", "VS"):
        assert code in PROVINCES, code
    # Olbia e Tempio (sigla ISTAT ancora SS) cadono nel riquadro della nuova provincia
    assert in_viewbox(40.92, 9.50, PROVINCES["OT"][1]) and not in_viewbox(40.92, 9.50, PROVINCES["SS"][1])
