# Authoritative GWT field names (DUO-Live spot, firmware V2.08)

Derived from the spot's own server classes in `ROOT.war`
(`javap -p de.zsa.gwt.zsalivespotwebapp.shared.*`). GWT serializes a DTO's fields
in **alphabetical order of the Java field name** (all non-static fields, public or
private), which is exactly the order they appear on the wire and in `pyvariovent`'s
decoded `GwtObject.fields`. So the index below is the index used in `models.py` /
`client.py`. Verified against live data (no offset).

Our own derived documentation; no manufacturer code, no secrets.

Operating-mode fields (LueftungsgeraetParameter): `betriebsart` (26) = **set** mode,
`betriebsart_ist` (27) = device-**confirmed** mode, `betriebsart_wochenplan` (28) =
mode the weekly schedule currently dictates. Effective active mode = field 28 when the
set mode is `wochenplan`, else field 26.

## Lueftungsgeraet (15 fields)

| idx | field | type |
|----:|-------|------|
| 0 | `adresse` | Long |
| 1 | `betriebsstunden` | Integer |
| 2 | `bezeichnung` | String |
| 3 | `ist_rechtes_geraet` | Short |
| 4 | `lueftertyp_string` | String |
| 5 | `paarisch_zugehoerig_zu_lg_uid` | Integer |
| 6 | `parameter` | LueftungsgeraetParameter |
| 7 | `raspberrypi_uid` | Integer |
| 8 | `raumart_string` | String |
| 9 | `raumart_uid` | Integer |
| 10 | `seriennr` | String |
| 11 | `totalLueftungsgeraeteCount` | Integer |
| 12 | `uid` | Integer |
| 13 | `wohneinheit_string` | String |
| 14 | `wohneinheit_uid` | Integer |

## LueftungsgeraetParameter (155 fields)

| idx | field | type |
|----:|-------|------|
| 0 | `ba_abwesenheit_dauer` | Short |
| 1 | `ba_abwesenheit_mit_feuchteschutz` | Short |
| 2 | `ba_abwesenheit_mit_luftguete` | Short |
| 3 | `ba_abwesenheit_zeitinterval` | Short |
| 4 | `ba_automatik_aussenluftfeuchtigkeit` | Short |
| 5 | `ba_automatik_aussenlufttemp_max` | Short |
| 6 | `ba_automatik_aussenlufttemp_min` | Short |
| 7 | `ba_automatik_aussenlufttemp_min2` | Short |
| 8 | `ba_automatik_innenluftfeuchtigkeit` | Short |
| 9 | `ba_automatik_intervalldauer` | Short |
| 10 | `ba_clean_dauer` | Short |
| 11 | `ba_clean_luefterstufe` | Short |
| 12 | `ba_clean_zeitpunkt` | String |
| 13 | `ba_feuchteabluft_abluftfeuchtigkeit1` | Short |
| 14 | `ba_feuchteabluft_abluftfeuchtigkeit2` | Short |
| 15 | `ba_feuchteabluft_abluftfeuchtigkeit3` | Short |
| 16 | `ba_feuchteabluft_laeuft_mit_fortluft` | Short |
| 17 | `ba_feuchteabluft_luefterstufen` | Short |
| 18 | `ba_feuchteabluft_start_luefterstufe` | Short |
| 19 | `ba_fortluft_abluftfeuchtigkeit` | Short |
| 20 | `ba_luftguete_rauchsensor_innen_wert1` | Integer |
| 21 | `ba_luftguete_rauchsensor_innen_wert2` | Integer |
| 22 | `ba_party_dauer` | Short |
| 23 | `ba_party_luefterstufe` | Short |
| 24 | `ba_zuluft_aussenluftfeuchtigkeit` | Short |
| 25 | `ba_zuluft_aussentemp` | Short |
| 26 | `betriebsart` | String |
| 27 | `betriebsart_ist` | String |
| 28 | `betriebsart_wochenplan` | String |
| 29 | `feuchte1` | Short |
| 30 | `feuchte2` | Short |
| 31 | `feuchtesensor1_ok` | Short |
| 32 | `feuchtesensor2_ok` | Short |
| 33 | `filterwechselintervall` | Integer |
| 34 | `frost_alarm` | Short |
| 35 | `funk_mindest_messzeit_in_sec` | Short |
| 36 | `funk_nb_aktivierung_sec` | Integer |
| 37 | `funk_nb_frostschutz_schwelle` | Short |
| 38 | `funk_nb_frostschutz_schwelle_wieder_einschalten` | Integer |
| 39 | `funk_nb_ok_schwelle_vdiode` | Integer |
| 40 | `funk_nb_pwm_aus_fuer_bq` | Short |
| 41 | `funk_nb_pwm_aus_fuer_pa` | Short |
| 42 | `funk_rs_ok_schwelle` | Integer |
| 43 | `funk_rs_reinigung_drehzahl_bq` | Short |
| 44 | `funk_rs_reinigung_drehzahl_pa` | Short |
| 45 | `funk_rs_reinigung_intervall_bei_alarm` | Integer |
| 46 | `funk_rs_schwelle_alarm` | Integer |
| 47 | `funk_rs_schwelle_kein_alarm` | Integer |
| 48 | `funk_sensoren_deaktiviert` | Short |
| 49 | `funk_ts_schwelle_alarm` | Short |
| 50 | `funk_ts_schwelle_kein_alarm` | Short |
| 51 | `kondenswasserschutz_erhoehung_stufe_prozent` | Short |
| 52 | `kondenswasserschutz_schwelle` | Short |
| 53 | `kondenswasserschutz_schwelle_aus` | Short |
| 54 | `liste_zeitplaene` | Vector<de.zsa.gwt.zsalivespotwebapp.shared.Zeitplan> |
| 55 | `luefter1_blaestrein` | Short |
| 56 | `luefter1_bq_stufe0_pwm` | Short |
| 57 | `luefter1_bq_stufe1_pwm` | Short |
| 58 | `luefter1_bq_stufe2_pwm` | Short |
| 59 | `luefter1_bq_stufe3_pwm` | Short |
| 60 | `luefter1_bq_stufe4_pwm` | Short |
| 61 | `luefter1_ok` | Short |
| 62 | `luefter2_blaestrein` | Short |
| 63 | `luefter2_bq_stufe0_pwm` | Short |
| 64 | `luefter2_bq_stufe1_pwm` | Short |
| 65 | `luefter2_bq_stufe2_pwm` | Short |
| 66 | `luefter2_bq_stufe3_pwm` | Short |
| 67 | `luefter2_bq_stufe4_pwm` | Short |
| 68 | `luefter2_ok` | Short |
| 69 | `luefter2_raus_stufe1_pwm` | Short |
| 70 | `luefter2_raus_stufe2_pwm` | Short |
| 71 | `luefter2_raus_stufe3_pwm` | Short |
| 72 | `luefter2_raus_stufe4_pwm` | Short |
| 73 | `luefter2_rein_stufe1_pwm` | Short |
| 74 | `luefter2_rein_stufe2_pwm` | Short |
| 75 | `luefter2_rein_stufe3_pwm` | Short |
| 76 | `luefter2_rein_stufe4_pwm` | Short |
| 77 | `luefter2_reserve_pwm` | Short |
| 78 | `luefter2_stufe0_pwm` | Short |
| 79 | `luefter3_bq_stufe0_pwm` | Short |
| 80 | `luefter3_bq_stufe1_pwm` | Short |
| 81 | `luefter3_bq_stufe2_pwm` | Short |
| 82 | `luefter3_bq_stufe3_pwm` | Short |
| 83 | `luefter3_bq_stufe4_pwm` | Short |
| 84 | `luefter4_bq_stufe0_pwm` | Short |
| 85 | `luefter4_bq_stufe1_pwm` | Short |
| 86 | `luefter4_bq_stufe2_pwm` | Short |
| 87 | `luefter4_bq_stufe3_pwm` | Short |
| 88 | `luefter4_bq_stufe4_pwm` | Short |
| 89 | `luefter_aktiv` | String |
| 90 | `luefter_bq1_ok` | Short |
| 91 | `luefter_bq1_upm` | Integer |
| 92 | `luefter_bq2_ok` | Short |
| 93 | `luefter_bq2_upm` | Integer |
| 94 | `luefter_bq3_ok` | Short |
| 95 | `luefter_bq3_upm` | Integer |
| 96 | `luefter_bq4_ok` | Short |
| 97 | `luefter_bq4_upm` | Integer |
| 98 | `luefter_raus_stufe1_pwm` | Short |
| 99 | `luefter_raus_stufe2_pwm` | Short |
| 100 | `luefter_raus_stufe3_pwm` | Short |
| 101 | `luefter_raus_stufe4_pwm` | Short |
| 102 | `luefter_rein_stufe1_pwm` | Short |
| 103 | `luefter_rein_stufe2_pwm` | Short |
| 104 | `luefter_rein_stufe3_pwm` | Short |
| 105 | `luefter_rein_stufe4_pwm` | Short |
| 106 | `luefter_reserve_pwm` | Short |
| 107 | `luefter_stufe0_pwm` | Short |
| 108 | `luefter_stufe_ist` | Short |
| 109 | `luefter_stufe_soll` | Short |
| 110 | `luefter_typ` | Short |
| 111 | `lueftungsgeraete_uid` | Integer |
| 112 | `luftguete_ampel_rauchsensor_innen_wert1` | Integer |
| 113 | `luftguete_ampel_rauchsensor_innen_wert2` | Integer |
| 114 | `rauchsensor_aussen_alarm` | Short |
| 115 | `rauchsensor_aussen_ok` | Short |
| 116 | `rauchsensor_aussen_wert` | Integer |
| 117 | `rauchsensor_innen_alarm` | Short |
| 118 | `rauchsensor_innen_ok` | Short |
| 119 | `rauchsensor_innen_wert` | Integer |
| 120 | `route1` | Long |
| 121 | `route2` | Long |
| 122 | `route3` | Long |
| 123 | `route4` | Long |
| 124 | `route5` | Long |
| 125 | `route_ist_fixiert` | Short |
| 126 | `sensoren_aktiv` | String |
| 127 | `signalstaerke` | Short |
| 128 | `silent_umschaltzeit_stufe1` | Short |
| 129 | `silent_umschaltzeit_stufe2` | Short |
| 130 | `silent_umschaltzeit_stufe3` | Short |
| 131 | `silent_umschaltzeit_stufe4` | Short |
| 132 | `temperatur1` | Short |
| 133 | `temperatur1_alarm` | Short |
| 134 | `temperatur1_nachkomma` | Short |
| 135 | `temperatur1_ok` | Short |
| 136 | `temperatur2` | Short |
| 137 | `temperatur2_alarm` | Short |
| 138 | `temperatur2_nachkomma` | Short |
| 139 | `temperatur2_ok` | Short |
| 140 | `temperatur3` | Short |
| 141 | `temperatur3_alarm` | Short |
| 142 | `temperatur3_nachkomma` | Short |
| 143 | `temperatur3_ok` | Short |
| 144 | `uid` | Integer |
| 145 | `wechsel_intervall` | Integer |
| 146 | `zweitraumanschluss_bogen_pascal` | Integer |
| 147 | `zweitraumanschluss_links_anzahl_boegen` | Short |
| 148 | `zweitraumanschluss_links_mit_zweitraumanschuss` | Short |
| 149 | `zweitraumanschluss_links_rohrmeter` | Short |
| 150 | `zweitraumanschluss_pascal_zu_pwm` | Integer |
| 151 | `zweitraumanschluss_rechts_anzahl_boegen` | Short |
| 152 | `zweitraumanschluss_rechts_mit_zweitraumanschuss` | Short |
| 153 | `zweitraumanschluss_rechts_rohrmeter` | Short |
| 154 | `zweitraumanschluss_rohr_pascal` | Integer |

## UserSession (23 fields)

| idx | field | type |
|----:|-------|------|
| 0 | `brand` | String |
| 1 | `brand_url` | String |
| 2 | `default_sprache` | String |
| 3 | `raspberrypi_bezeichnung` | String |
| 4 | `raspberrypi_brand` | String |
| 5 | `raspberrypi_ip` | String |
| 6 | `raspberrypi_kaminmodus` | Short |
| 7 | `raspberrypi_ort` | String |
| 8 | `raspberrypi_plz` | String |
| 9 | `raspberrypi_reduzierte_ansicht` | Short |
| 10 | `raspberrypi_routeberechnung_aktiv` | Short |
| 11 | `raspberrypi_seriennr` | String |
| 12 | `raspberrypi_strasse` | String |
| 13 | `raspberrypi_uid` | Integer |
| 14 | `raspberrypi_zeitdifferenz` | Short |
| 15 | `sessionUUID` | String |
| 16 | `sysconfig` | HashMap<String, String> |
| 17 | `userId` | Long |
| 18 | `userName` | String |
| 19 | `userTyp` | String |
| 20 | `user_rechte` | UserRechte |
| 21 | `wizard_ist_aktiv` | Short |
| 22 | `wizard_step` | Integer |

## UserRechteLueftungsgeraete (25 fields)

| idx | field | type |
|----:|-------|------|
| 0 | `ba` | Short |
| 1 | `ba_abwesenheit` | Short |
| 2 | `ba_aus` | Short |
| 3 | `ba_automatik` | Short |
| 4 | `ba_feuchteabluft` | Short |
| 5 | `ba_fortluft` | Short |
| 6 | `ba_luftguete` | Short |
| 7 | `ba_normalbetrieb` | Short |
| 8 | `ba_party` | Short |
| 9 | `ba_sommer` | Short |
| 10 | `ba_wochenplan` | Short |
| 11 | `ba_zuluft` | Short |
| 12 | `lg_info` | String |
| 13 | `luefter_typ` | Short |
| 14 | `luefterstufe` | Short |
| 15 | `luefterstufe0` | Short |
| 16 | `luefterstufe1` | Short |
| 17 | `luefterstufe2` | Short |
| 18 | `luefterstufe3` | Short |
| 19 | `luefterstufe4` | Short |
| 20 | `lueftungsgeraete_uid` | Integer |
| 21 | `totalCount` | Integer |
| 22 | `uid` | Integer |
| 23 | `user_uid` | Long |
| 24 | `wochenplan_zeitplan` | Short |

## Raspberrypi (18 fields)

| idx | field | type |
|----:|-------|------|
| 0 | `bezeichnung` | String |
| 1 | `brand` | String |
| 2 | `datum_uhrzeit` | Date |
| 3 | `ip` | String |
| 4 | `kaminmodus` | Short |
| 5 | `manuelle_zeiteinstellung` | Short |
| 6 | `ort` | String |
| 7 | `plz` | String |
| 8 | `reduzierte_ansicht` | Short |
| 9 | `routeberechnung_aktiv` | Short |
| 10 | `seriennr` | String |
| 11 | `strasse` | String |
| 12 | `super_pin` | String |
| 13 | `totalCount` | Integer |
| 14 | `uid` | Integer |
| 15 | `wlan_psk` | String |
| 16 | `wlan_ssid` | String |
| 17 | `zeitdifferenz` | Short |

## ServerInfos (4 fields)

| idx | field | type |
|----:|-------|------|
| 0 | `auslastung` | String |
| 1 | `cpu_temp` | String |
| 2 | `server_timezone` | String |
| 3 | `server_zeit` | String |

## VersionInfos (2 fields)

| idx | field | type |
|----:|-------|------|
| 0 | `mk_version` | String |
| 1 | `tw_version` | String |

## Raumart (3 fields)

| idx | field | type |
|----:|-------|------|
| 0 | `bezeichnung` | String |
| 1 | `totalCount` | Integer |
| 2 | `uid` | Integer |

