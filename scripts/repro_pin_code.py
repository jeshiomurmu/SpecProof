"""Reproduce finding F-1f37a3fc: py-unifi-access User.pin_code (str | None) vs the PDF.

Fields below are copied from the user object in the PDF's section 3.4 Fetch User response
sample (pages 17-18). That sample as a whole is malformed JSON (finding F-13962a9e: a doubled
"{"), so the relevant user fields are used directly.
"""

from unifi_access_api.models.user import User

sample = {
    "id": "17d2f099-99df-429b-becb-1399a6937e5a",
    "first_name": "Fist Name",
    "last_name": "Last Name",
    "status": "ACTIVE",
    "pin_code": {"token": "5f742ee4424e5a7dd265de3461009b9ebafa1fb9d6b15018842055cc0466ac56"},
}

try:
    User.model_validate(sample)
    print("parsed OK - finding NOT reproduced")
except Exception as exc:
    print("Client model rejects the documented pin_code object:\n")
    print(exc)
