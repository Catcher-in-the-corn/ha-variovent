# Auto-extracted from the DUO-Live Control Center web app (spot firmware V2.08).
# For every serializable DTO: the sequence of field kinds in wire order.
#   'o' = object (self-describing, boxed values / nested DTOs / collections / null)
#   's' = string (index into the string table)
from __future__ import annotations

PKG = "de.zsa.gwt.zsalivespotwebapp.shared."

LAYOUTS: dict[str, str] = {
    "de.zsa.gwt.zsalivespotwebapp.shared.Debug/1465752257": "osooso",
    "de.zsa.gwt.zsalivespotwebapp.shared.Fehlermeldung/4068454655": "ssosoooso",
    "de.zsa.gwt.zsalivespotwebapp.shared.FehlermeldungFuerEmailCronjob/1053318709": "ossssosssosoooso",
    "de.zsa.gwt.zsalivespotwebapp.shared.Kommunikation/3573781985": "ossooooooooooooooooooooosoosso",
    "de.zsa.gwt.zsalivespotwebapp.shared.Lueftungsgeraet/3252019805": "oososooososooso",
    "de.zsa.gwt.zsalivespotwebapp.shared.LueftungsgeraetLuefterstufen/4082224619": "ooo",
    "de.zsa.gwt.zsalivespotwebapp.shared.LueftungsgeraetParameter/2221229652": "oooooooooooosooooooooooooosssoooooooooooooooooooooooooooooooooooooooooooooooooooooooooooosoooooooooooooooooooooooooooooooooooosoooooooooooooooooooooooooooo",
    "de.zsa.gwt.zsalivespotwebapp.shared.MyResult/187169326": "oooooooooooooooooooooooooosoooooooooooooo",
    "de.zsa.gwt.zsalivespotwebapp.shared.Raspberrypi/1348886694": "ssosoossoosssoosso",
    "de.zsa.gwt.zsalivespotwebapp.shared.Raumart/561650512": "soo",
    "de.zsa.gwt.zsalivespotwebapp.shared.ServerInfos/4187381153": "ssss",
    "de.zsa.gwt.zsalivespotwebapp.shared.Status/1445550016": "soo",
    "de.zsa.gwt.zsalivespotwebapp.shared.User/2116479947": "osssssssssosssssssssoossoososs",
    "de.zsa.gwt.zsalivespotwebapp.shared.UserRechte/4230333573": "oooooooooooooooooo",
    "de.zsa.gwt.zsalivespotwebapp.shared.UserRechteLueftungsgeraete/1048840838": "oooooooooooosoooooooooooo",
    "de.zsa.gwt.zsalivespotwebapp.shared.UserSession/2592594343": "ssssssossoossoosoossooo",
    "de.zsa.gwt.zsalivespotwebapp.shared.UserWohneinheit/3166164147": "oooso",
    "de.zsa.gwt.zsalivespotwebapp.shared.VersionInfos/21385331": "ss",
    "de.zsa.gwt.zsalivespotwebapp.shared.WaermerueckgewinnungErgebnis/2677127708": "ooooooo",
    "de.zsa.gwt.zsalivespotwebapp.shared.Wohneinheit/1665474216": "soo",
    "de.zsa.gwt.zsalivespotwebapp.shared.WohneinheitMitSpalteUserWohneinheit/3974939476": "osoo",
    "de.zsa.gwt.zsalivespotwebapp.shared.Zeitplan/461838795": "ooooosssssooooooosssssssssss",
    # exceptions that may come back as //EX
    "com.google.gwt.user.client.rpc.IncompatibleRemoteServiceException/3936916533": "s",
    "com.google.gwt.user.client.rpc.RpcTokenException/2345075298": "s",
    "java.lang.IllegalArgumentException/1755012560": "s",
    "java.lang.NumberFormatException/3305228476": "s",
}

ENUMS: set[str] = {"de.zsa.gwt.zsalivespotwebapp.shared.MyResult$resultCode/2976108651"}
