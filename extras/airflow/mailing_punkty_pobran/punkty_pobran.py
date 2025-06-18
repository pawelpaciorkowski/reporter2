import datetime
import json
import time

import weasyprint
from datasources.centrum import Centrum, CentrumPostgres, CentrumManager
from datasources.connections import get_centrum_connection
from outlib.email import Email, PsajdakSender
import sentry_sdk
import sys
import unicodedata
import re
import io
from base64 import b64encode
import code128

sentry_sdk.init("http://f528eea41b4c4339bf56241de3172a2d@2.0.205.117:9000/12")

LOGO = "iVBORw0KGgoAAAANSUhEUgAAAVgAAABPCAAAAACLo4ILAAAACXBIWXMAAArwAAAK8AFCrDSYAAAAB3RJTUUH4woTETY7ceuSSgAAAB1pVFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVBkLmUHAAAfQklEQVR42t18aYxk13Xe9933qnrvrt7X6uptmpx9hsNFpChSZLRRspbEiRJDcOL8CBBkAfIjQQIkgWMkkfJDlg0jCOw/BiRFUWJLsmVJUUiJsiVuGg630azdPd3V1fu+b7W8++XHe7X1PuTIGvoB5HRV3Xfffeee+51zvnPupcV+l2AkyaZTHkpd1xFxzIsCCIECBCL7/8PaH6NXCO+PSwBByD34fWUXrg8vZ0x19GS3g0A6R8pBu/4FeKz2f1Mu+i8lHqCxhM28eXkaBGCrH/5gBeXobrR2nwfqbnVP5PtV8AcJFrDey3+1Y4wFIOHhj1eS73oOVShY4T0Jlu8PScsc9IOuv5w0EAnC8K1XPd3dws3Pg/w7pQMfdVAPhLTf7+96jv8arwMFm3xzI/t2BtCVcYDEe38jHS6j3Z91PKR+fwhWADSRoAlUBjTcGLQ6WOkO0MN8+/3+ysJEoSxZIEEFCBL8zoLB6X2ssePpouFrwjuk9W6reIh+aU/jAsHysHt5JHjc74IlAK2LhZJwNjLHfBvmb2KuC9J37wBTtNh3YahV0bJQgbmTlDWAvCeY9CvSWBLWN+X+K9jjOp2BMPbRNUG+IAvVV0fHAbngxI89QPt+8A0OFGylDBVEUYJU6RLHj78Kw4NACIKvryqyUyzwAQQWr/di7c46FuJR0dz9LFi0ulnfkzAAW12Qx5VsUTPLIvBlgQrv1sxs/yT9OcirNAlkZ0W8/yO2A0Pa9tZJZW20hJJuUsfDAgI2v1aVW8tUgCiUCO1azSq0SgIoSbmpVLa938AjJYL3MSIcKNiK05P+S1EAdLLnuGuPgJBZzelrRakRczpml/ypcmr3AqUILeSWkFsTYKrfcElk1pjJcV3Xlbmf1fZAwToXBkcDOyyg/ELobkBNP/pGNlTWx/8hiKzmcfgrawKgS/+sAtqFlQSGfi87I975f1XG7AIgN//HjQL4dcPVde3d/e33ceDgHqh41efHPBMYanuyhzo2woqZq4PZtrb575cXvL8dXhVh2WQg7tZZ6vY7OfdjZ75Txn8mAcZHgmlQgMYKd3zoEz33bXRr9rpLwcuac6clwFrQ1px3jxce+Hdq9SYgQYBFYrHQMy0IpuizLHk/VrCDniCIJBeHd3tfykaCBjRkcuTrX7n214YGh83gfgGLOciki6WPRXyTYflQjzm+IaYwOUmQsoDhQvxAf2EXn2bs6nUBkBGg9C3tE6eVnjjR21ZJK8BQV/5k632Dscz7n52nX6UMwNpzxqfFjylXDGwCUP/mJIHkwJNU7m4dGATLWIxPAEJr3U2AdihZWqgm1kDUQ/+2xEvOXX1h2Ddsrw1ePCZt+Z7Jo0O4Yd6NHwvQOVkqUfIebDh+DEkBmZseJF3qEwDdTvrkJA8PgiVwaIui7XqCAjA6v7sVIVNb29hx8bf+ScRnFbdnfukQsAcj32OAAIBtTRaSQn0OgnD0WG6sVu9QgHs6ZgBwdJH24HFJeWIhfT0DA9PZ78qCi2Pc5zVJQ/KxPggClTwSGln44Hdn64oswTHx91DBlnSQACIt5i68GivEx0WouquHFuT82HHgmQDWhkHAOdFRTQOTuqM9AUQ2MitpVI6XOfhNf5WBrznsRU0DBaqqwtzdCG9tAVBbc2clAOwM6RDShAUk2ugkAFvWWVcPwdqbGe4aKH1/y4COjA5Wv0C9uMdi3z3hmOV/74FXkKf6WGUAsMrIaD869YArOSAAJlreGAEBezudTwEdOkE3Ngmwua2ijQQ4uljgORdwN7QwJgBd7jNuyGo/QkJ6l0Tuu7nNHDpZLkUpVKBwR2quBZYH4QDsdStaIQDx1YIE2CG2Oz1oIaGtyo15gsFcPPdGLOAdZEkrQ1Hc75XlLa0seQp0jTnh2OT6xqbVu5AqeRQ2e5lUOq3C93MPNfCyEOjhLugOAmNzRmC4GyXRywA5M9rIYyw5Lg2KAPtK0RXyKG4PPWZY7PAEdJsAioJ19olO7LUXMpG/17BnXN5fXsOpj5TcteXSURGnaKdeTeKh04V6d2g0pU0Qhjs+k3Rcwer6NgDVxOjGKIlbdyB7DM0YmyUIp4+MlkOABj0UcmQMCmskIeOTt3vnW/Lii6uVkT3f283BhaXq0LuBAnsUFij+1vWB4gVpDnlR2QUrSmupu0EZ7dy0ANhcB3aUCJIGvKMhRNDNLUmoiUHNDYCA4ZXiGcshp1JLvkVB+d5hbyVgesxexVtcRFmUd+tyiZBs2h6IhQKUniotb20p+s09RPVsZopGtKtL5TTHlazMwjBEobcc6KhJCtCdlfpjvEDyBiGivp6obh0hgbnJxiIvxYdUgbo+4qNtbftewc4vo7yTCBjcPLonkmhsxF1S5IS0uTThPVxemAgp8moEuU8+AaeuaPkchrF2bgKiuD3aZjxzbEgaWSAl00egrmkWBOZm6u2R92tpWDCwXdVgKAoAXL95oZAwhwjsQHbz7e/MEYLMx/r3YGwmsYOmJog+O54zXpkRsKskq665fo8wHoK8569vfSB8yHwQTluW4cw9zz1EYTWYJEHa2w+VH9vhph1IikD5CYBlHdcAcG3gFI+ekKF5EGB3iNbEXI+ABjOhAi8KBK79jqPt+dlNI0jVn/zCnvErdQeIudztjmlxGm6PyRITOTHZo0am1eEtt9s5PDLLGTgeqbEWWrwRFMKN3j7vHjcz6iVvigBqmx3B7aEA2FufdY+ekYEdAih9AAKj4aRE3FmrLwQ7CKs/83OOciItpx9/OLxXDouzCPcwiMEFkw0rJrZQ32oDG+hDSoFJzCmkUTZ5HCi3N7nOSNQaZn/wDblycmJOVWmhrAa4+YwUs04MJdIyc2XaR1bat7rq/ASY6Fd4BmMpTo74/c+MEKCidSLQ7qZIYWit9iiQ5vZtEbA17aDQUjNDwkxP1OfGFyAeCWMBmPr+M50OC5/tX+ObaGghKG9zYWVbpfXNpQaQF/fQyZmlZLi50YCwyKysbqXCVQ0VNLL00qCTWlxtr5OSa2s7prQm4oBIZeIp01SSCVkDL7W6nXbLakppQNmM6Hgb21WVkuj6HklqKym3rNwxboG0ckbOf+61Kzn1Hn7tYyHQBv5ONpakPFOIVf63Q4sAxFhYpNorlyFgYqr2SIidGyYF094IAbWNsxS0eeecrwG+qghQBPJSKTA1OPC9tqc+E8svQRGQMqNAtIxQ5vJbc0kYhfs/WQ9oa4LO1p+PJD22frobkKZeH9zwPCfU+sGzAnXlTcYqbs3oCxHv7WvT24JTdf6ZEnk/Hpmjxr4WfbZCm1cG5tLWCTU9dg6Qhl5Ot7QPx3c+ffH6L9TwdJVkF94eXkqRlX1P1bnZkDpbQQCItJbe4M/SeWW+XP14aK/HUUhRZv/wbmYAwPQ6gNBQuwxRW0OndEjgJRC4swAB6CgFgPKOa6CFbntOoR0hHvnnIbuxOPjGLVKZsa8n/mVXvp4DAO3aJE2nAbzXXkiVPRSZv5m+fqrWkSaWlV5sPTM5jemZLtJO/99htLbpZjIROlFGpQcmMOO54ZY2++qLydLeksWJ5Ct9PVxJzKUIzkdLtfX8FVREOb2xke6upuzwECavbpeUN9mB63q0VMws/uC26upT09sLDY+7e4lHQjSZ2z+Zdp1cyJP5iZ5waPyEgjmMi925IyOoMgYAqGoeAYnMHR/dDwkN7Y00AJg+BwCcbmNF4M56JJBpUM1R0hem8NHBP3oZjoCX+v/prjmaWlJ1p6Gdez3tfvSSWZ1bYAaQHcmY+k/GdPtbViFR3pvDpu+5Ohu+jNWMyKVpqurh7iqnYvJyquQTFzj2zW2loMjnXn7H9n4sXGHsW2+y/hO9eu3HWk2R2IlT9sET9U7L+jjcbkJ65TbOPFO/9acJbsjN2XplrTpEm7ry2rID+P6KCJN8cePROh+zTU6KKoh0FRiB6VEIQFO7ACDc83NA1J2tqsABOoDdlw+xCnf5AWunYwlofKLGf5xhtsSIIPXAR173a8neWKsu8pkUF1prRAzN285zIXgpORGAyXHqfLdjBZU0EnbqGsz5ZmQsWBai7PiGwh8561D21iJjF8JyZdxKwomseYy1OtTGVYtz/Y51KdeVMDMnPvMhl9DUMqvaCTtzE6WPtAIOUQY34AEK8kuy6ZG3bwWsfxa7mH5p4uLJchaWvJuiUiJaCsDgAgAyWuUb3i5aAhid6j+0klCaTgAA6jr8LturliBiI34mayiznqKfh+yp8PPkS5vVhQij7TGw1zFKZ7rTD5QbTa6zronQ/LxK+xyj8YxpbKTs8Lqp6zHITIvREOCNZnDylAtyZ6nR9IcdbyKJxjpISzMId7pGGJtj6IRr7KRFQznhTSTRfinkQJmEh9ZagNOqaIs62lqGU29cn5CCrOdJdGl31kYHEykYQJBfKk/BsTY+9k5/T23YCNbCcYxjcxUVQDbQ0a2MAaxmvuar/4SbBsCV4RP7EjnKQfzgIgAh+WclAMSNNEDCu/VciPlGzNXVlIZ3gxAFWs0v2IoYhfAHn/Bco0zcKlpJ2XgS9U3UzjhsNExlxqBoFTW7QBMztJsTML0hECp7zthyY71xqbOEzCTWVdtiBC+etq3N1NoE0OkCmVGgq8oASsaFbpdAf7tC5bSTq6pqpgsBUmokPr+RkVti0ptbWyQNIFFe1nplDKl4vLSquoTpDYuyhs6+KmevqFZv+qBw66bJsaMkvJsfozmMNtSgZyRq8RsFZJKg4a0a0O5iHSm/MwokqCCXDMGO7LClgbQIWSe1ll4ZhxNzjJcetewN087M0+lyoOUpOF0ONJ5EpN1QU0us6nRAAdWS3U7NTSLUaUSbALsqQbszIdMVpp1cRWmvoV2ZhNvtiNDsHMq7DIDqSsHLeHExFjGuP5w3bqVysT5oAmioqK+tDHmbKwvraQcAjbe9PRe0G3mz89JFZ/ceBs1MELCAoxyGEoAZ2a4M1vLuyfA/r99gNhFMQtlYlBNz1bl8fI4zssx66j7emOzuEWUSUEeIkqaHx5a20l6KVTFarU0hFHOosW3UdRhofIMVUSo9IrRXw2o0w/Z6AsZmFsYnFzdTdlk1HUZam5CJAdT8nMJdRkp4amw2smMbqG8nQY0n0dxkaJWZmZrd2ErNiF0GrkDv1gtzxuRflJAgt+vBvohDQHbjzu07abK4ql0jk6tPhXbFB7i15qe6C3IOMgLH5yoDIWqPqyUAU2MiZemzPSSDurrFkb4g4i+OGfP181Q2LBWwNM1wj6HsSz9fZXV1+WRKzRFAiU3WtUNenIhWE3bUY1sdtTgFdRkwOW5NlwGkzGuvz9vyyvA8EK0SNLnCmg5ISiRNbTu5MwZESyyV8BCtBCEvTnWEITv92q1NhMuSKVbFDFzCS/x43uzaB+Cx49KZ8sA7Ut3DF2+8eWd3IsRJ/bTiEYdFFj5zy6Ox0GNPZb8f+TNZQovxnmzyyBaVgwZ/Da0Blmz9XEXw9dK3lwwAe/ujZGF2S0WcjLJ+igDQw9imrW8j7JUXM86T5yOpb24yFqJswqKjAlqaBXsMtDFu1OVC4+sq76TF4izDHYRkL/8oZZ44U7f1f+ZMzDGyCav2GgNk4kBnOTQ9D7fLAOvjNDEaQUuTCnVTWvrxLXSc6yx/6Yqa6yBXyrw+Y7iL0eGlJ5sc+QtahOOc73rtFVvk7YomdeVEER9ovI07oijnw7+ezRHe/tGqAZAefDZbX7vb6xIA74YHEfb8F9xA+9bfXAYAe2u7vBiaCxOMmXxVswgyE7eMVkCbv8jw4rMhzM6itIfi1jjYZYTRNZRHCU0t29JuykuAHQ2kN7KNxiYKWH8r5Tz68ZDmllQdI7Q9atHlElqakukkMyPbrGkFvKklVHZSgB3bYKSNsG/dMpGPdzG9DERdyljNDO7eAuThQ881O/TjVX9Dkol85Fl3lziIqQFbTBaMjgGAqehn9mrx+V/d3Ar0a1/ztTEoEDB9rl83QJa3+8+YmMV+zkQqIyATlCpb+XaBG5Mw3YSdn6Lpd6nxlOqbaezEEqqipJcgW2opO5ZBQxOxMQ52hmgzcSFWSgNNzdJ9MGQ0lkFLPaHpeVZ1G0DjG6zqNNYbJzojhhrLsDVCyHqjUmc5tHMH9kTM5cIUS7oNjYGmt3bnB/jYMxVBHtRPpok0oQ89jeLyNhkkPBTm+zSwDgK2qS3XVXnUb52Yt9kE9p59B9LYuAio/MEcb+T0GBCwSyMqxgDfUE1tET4bk7VbgOzECivbASVSiLQZeKMW0TBl42m0R6iNCTHmUqmERSxETS0jFDPE2gxD3Q4EG/fU0OogFZc6Xb+j1gZS3qjUFgEXZ2Q6HWonDnW6ALE5ARNzqLk5mJhLjG2hodUAxmhld4Je/U+V0vduc7ZClqEnLu2p+FnK7qXxzX/6lh9e9VTn+OVwjxFALidYQNb422MkCVaivblqJKk+qqxlYncYApz0ncLFH5RpaOvn274/aHIV3wLsaFptESozIrVXQatTcGIGSo2J3S4xuWRD3Uaam6ETM7CJNOpaCE2sKdJhAGzHha5ya+dnUNplgMwY0BGCsDkBdLm0k1usiBFamFXpCQMI08uoihlhPIVIp4FN0MbKQLmAtyuCV+UHaoyRv4koCAFEUmWPJRaLckGkZ4vCp7UhGYjoC+eLVmKOBxGpoaeDRhSJ5HBZ9qZwp83c9tv21uZH0lEzBxl5t3ZKnQKqZztjUluJn343SNpGqwNHBoCSCZheh3Zpiog6sKMriEQN7fwcSzooL+6hqZXQxBZro9R2nOgtBxS3iFWQVnMLdDoJm9hiYyugpRm6nQQ0u2xKopQ34qGtnsi5WPQSabTWUplRy/ZqaHnShmKkhQuUCAXnCkg6e8KBisNPP5vfev5FMcA1QpAtdQuy78DYNAGDsgeyCXNR0aplEvAGkiVBVEsR7/ybXN+n/mPN6pC/Kk6UIEspsK5plhCc+EKgxjIC3vn3sNvry+v0+3cfK8nHb5qbR3mnIWa2UdIEu30TilUTSiRZFpEWhoCuMhpvwVFNmbVDsyx5wKE2x6iooWinUyhthd0cFDpLCTuxgbp2CJhLmYp62Kk48IAL2TjUGYKInTjU5QArU0QzrTewzOp2iHLFescWxvGqOefux0qT4iPjAz5KBqk90+IUKfvNDYBCU3fBd431yyLE+GJbPn9BLOVzXQbj0wYAyvqRf3Jl9y9ACEvDnYHoBJjNNygQDgRKzueeK3x8IonGRgKrnkkPl2/fuGUQc2C9EWFroGf1zVlWnzQUPMuNeMPEaylc6CI0tajKDlpKixaZifDmG0NwYwQwa+ms2BopDWTmnJVXV9B7yhWXJg07CVrNz6G82yFWN6nNpHvnjQzaqwnAFaN186Lopw4gPBzNJ4YK3SMZVT0ytpPfjUUb6nELMFeZGz7cxerzVA2qO++IIOfibcxz/QV8lITbGxCh2pifxxBBsMdYgtoZfNqAoIw1NheegZ5T2vvsZysLot3MKBEtsY6pNPReej0cCaWrOmmxNKmylh+WprYZ/kAnIdMWTs58K7SV5LnHQ5BGkmhrpBFZKrPzvTK4RKTdAHLEqa8/+KkSNpZkVv6kbGeVHU9Wg0qsqb6DAG1iG42NwYq5kjB2gexyCcAlqs//2Jqsry31POwY5eL8QkCw5AOXXsmDhEV/X6GvpcXtVoDAWTfP2TJ0agASaResA6BtTyVAC9LLrRCoCw1BKAUA6O7ZIgCtJcsAtMyzIMBzSqubu/r6G4sial46q5ihdHotsVne2l03aCsaKYSfVkXPtaHV+qb+My5B87A7sJhmVVP3yXICtu1ZRV0K4NmV8UxJtL9ySLURGJlza+NJVYfABz95YyG9FeruPd1iIOucZWsVAajkLLtKaGz00s0UbHdPfK2kj1n6dfW7t7LIaVH9a6eM8ZNw2sXxA9L89wcM6W8NUt1nTuSsspHgzfrqWF1RGCptL/tMankNiMysvzOjINAwTZyVQKmkvvC+zLxAUabFCJoJtoj5PHsoFCpxdtVeyE93+5xBxoT9FWMkSEbyUgw7oAFg5aUlEzb0c4cCrUMANr1jnTKfkncgKb2VRnWYona203TLwgYGgqyMAQGmBToAkF7dMVVlFOWSguhRdvzFAROUmtQ9c9HNba7Ku5yS8YuUlHhxyPh+gm165qxbsFlQBZR3YbmTiuW4b7FJlmTnfuWF1uSKjJTvJeux5DZTk5bBNrvc7wWPNTa70dLfyprf85ut7KCFdYrOsvE/mGDzrs9N+v9RPucW3GuNigl/0UKwC5evbkBGbt9j/c7+pZHwk4nWzv386o6sI/fkoz1OMcfqi1R7yCsZFTwafp3gbo4rO9RCT4Ta1SLIGhubc7BtwXD99H6R9HP1yhRhmd1XmpV6gNe2kEWHdnP4yqeyVbSjOCDr8mU3yk+zFShlpkent536WHcpDUTIaI9gZQRaKDMRn02GGmJdYZqC+k7tQwbiyO8KeGqqCNL9jYd77lHhcUpUkWD3eVjxPwViyeb/VZj4D7ydIGsSTF+2CgEsYtXFXHKKQS9+8U3wJM9XOisrksaoOB9Fm0/p52vvJJpdYUXheVv35OKus3l2773lXmFnPZijy27uroLL5iOlo8u/ESwLmztlaLdQsjPFw1SvcN39co8dO9aMHXcEdzfSPf7RoZLN4rYIZc1C8UxS+y3BnLOeNWr5x/4yNmMXGsf99prtsVPZuuQiEe65L0c3HnZQyvGmct9m/ibAPIzuVezdH/0Ef/FpDkfWwR82rLvSnHvV093Wct5V28DCFk/iu1U6arep2288e6Z3r77dVelq4doJTkRSEUIfJsHDFjdR6Gze7QgZuKe78eGIivZ953uf3R/HMSGHnyd5jJHsv6yOv+/3l2cSrN5b5+/eYB2lEYf3vHvYRy21fY0w9ncKDxfJkQ2yye4DZu6wA7QObU7uAd/3Mm/7aOl+Qzh6eo+pAMqRoO9KpfMBwr3TfhkbYBN3g3YQkihXI1A053lgzEVKxZuAgvCtQFlp7+9jjGTuIaowVwct5A9zKlyIzNVhmTxeD1zP5NPDhTmY/Kfk9UkF9FsQL9nR256k+G17AOj/qq97KFg/VZor1swb6Cztyt0uoiHI9f/9x3PKOhHBrQp+zE7G6H/6XtbUBZ0u/8ErFmbjv7+iI23gr+Zy76HGZhGwqBg5T6TIFoo2cJ4tqv6x1ww/UM8DU2HxI0St7KiAVAE40/CUkWaanjHQfQkK7j0UK7R+ZaHifNvNBbiXrpZuzJ04rSsT7DnP+O3N6MPrV4GzlZdnwv0nQc3dfsh5g49uXr+wuN3BN8bRczH1evXqiXHnwvDCw1fHowqfzbwxWdLfr8vznkP7tux09CJuDqeij5rRkbaZbk4MNk5HnfsTbJ3fvmeCBfTVP65/Pv7YwI1vXj/7lZecb00/+daXSgb+34XwV17hN5vLLv/k22eu/17Da1ceKyff/tLJhf/280fe/qNLX//LZ27+15LhH5z1fvuFrdj3X3ziq1cf/PI7+sO1p57/cvUvfvbI/H8eD79z+uyXf1D2FwMfnP3i7M7/bKv7yuWSb0Sb/+DFiq/V9ZOBqbivVPeeYawEbF+r+s2e6ysf/lDmYkO6+R91Tacin/0HZ6aWVm93fbZ1pfs3a9p7mj//G72j64Zoc2Zmo5WzM5H6VNpUf+rz52cWmTrz786dmJ1J9HH29N+tTGvI++yF+PzW8qPPVZHpyBf6ZrZnhi7+7fTI1njFJz5RsX6j7de7VrwsKOtvKsYCSsvQWrzsPW1oDMnSza9OWXoZp/9LZbj25t9pmZ39wwFBQF3zFPsmJia7KgGEk19dlAUqS/lA5sbaedAlgTRMyBPh+NPvOKBnHKNUw2f+17d+49ScRfcXw86xqa/3qVdAQIYWwOQrj572rY5e/M6lJ5zgTJXMTyufyfzwpQ9foAhUdo0luhuHp3sdQD/704eeML5XEK19vaIr78Dlc7rMrQzRfPpfLP7+WwDkBR7cfWfB7p1gld2xwL+afjrkS9pslpysBGjs8H94fujlD/ZirexUGQDS7Rmd6+oYXO4SwI3wA9WB61p74u3OOiC57QEuYSkLz1NwQLg1xnp0539/5bcm3vSIid/58/Q9jPPuV6+g/OT3vz16Kny1cnD5EePKcVG3+fwmUd2b+H6iYnhj6ZsfqL/8F9MuJCK20NAYna5po0vWbf7II+A4MM7JF065NaevVi3R9GR+ONHduFP+VnrHWLpwjGnq+MWC6Q5Pj53zGmtOxL879BE3G1rcX7K9p14Belsyp3+tuep0dUV/07lY5ExPa0vk9MVztb0VZc89XdbbXtrd19x84dzpUlCRjg+cjEQfP+PWnO5va448+ND5muZzbdDwtc+3hiMXz71R90xPZ6b9M321jXUPPH6uJXK2u/rsA00xt/RTH66Ilrof/2h5V03Jcx9z7s9zI+8lV0Brg/NMfayFsidNirkKDv+zQ3ks2JIgv0KfBpnfHfjdyMQXO/7Wf3nyX/sHS1K2MDUq/ygz65cE8D49NVL31Cswxposcx3sJciSZyZ7DJ8RLY2f0/F3w1m/ZinYMruGJ6vZ8uSr3zn1rJM7dj5XLJ8leQQDONpdrnQ/aax3z+Yod0Yscun9ouOdCjJWPIiJJeymWwpp3SsrlUMLkSqkupjbfeAn6cX7kunS/wcFTpl0zndF4wAAAABJRU5ErkJggg=="

SQL_BRAKI_BLEDY = """
    select w.datarejestracji as DATA, z.godzinarejestracji as GODZ, z.numer as NUMER, o.nazwa as PPOBRAN,
		(pa.Nazwisko || ' ' || pa.Imiona) as PACJENT,
		coalesce(cast(pa.PESEL as varchar(12)),'') as PESEL, pa.telefon as TELEFON,
		m.nazwa as MATERIAL, bl.symbol as BLAD_SYMBOL, bl.nazwa as BLAD,
		z.kodkreskowy as KOD,
		(cast(list(trim(b.symbol), ' ') as varchar(2000))) as BADANIA
		from wykonania w
			left outer join zlecenia z on z.id=w.zlecenie
			left outer join pacjenci pa on pa.id=z.pacjent
			left outer join oddzialy o on o.id=z.oddzial
			left outer join platnicy p on p.id=w.platnik
			left outer join badania b on b.id=w.badanie
			left outer join grupybadan gb on gb.id=b.grupa
			left outer join materialy m on m.id=w.material
			left outer join rejestracje r on r.id=z.rejestracja
			left outer join bledywykonania bl on bl.id=w.bladwykonania
			left outer join pracownicy pr on pr.id = z.pracownikodrejestracji
			left outer join kanaly k on k.id = pr.kanalinternetowy
		where
			((w.datarejestracji= 'YESTERDAY' and w.dystrybucja is null) or (w.zatwierdzone between addHour(current_timestamp, -24) and current_timestamp and w.bladwykonania is not null)) 
			 and b.pakiet=0 and k.symbol = ? and w.anulowane is null and gb.symbol <> 'TECHNIC'
		group by w.datarejestracji, z.godzinarejestracji, z.numer, o.nazwa, pa.Nazwisko, pa.Imiona, pa.telefon, pa.Pesel, m.nazwa, bl.symbol, bl.nazwa, z.kodkreskowy
		order by o.nazwa, w.datarejestracji, z.numer;
"""

SQL_KRYTYCZNE = """
    select z.DataRejestracji as DATA, z.Numer as NUMER, o.nazwa as PPOBRAN , (pa.Nazwisko || ' ' || pa.Imiona) as PACJENT, 
		coalesce(cast(pa.PESEL as varchar(12)),'') as PESEL, pa.telefon as TELEFON, z.kodkreskowy as KOD,
		(cast(list(trim(b.symbol), ' ') as varchar(2000))) as BADANIA
		from Wykonania w
			left outer join Wyniki wy on wy.Wykonanie = w.ID
			left outer join Parametry p on p.ID = wy.Parametr
			left outer join Normy N on N.Id=wy.Norma
			left outer join Badania b on b.ID = w.Badanie
			left outer join Zlecenia z on z.ID = w.Zlecenie
			left outer join Pacjenci pa on pa.ID = z.Pacjent
			left outer join ODDZIALY o on O.ID=z.ODDZIAL
			left outer join Platnicy pl on pl.id=w.Platnik
			left outer join pracownicy pr on pr.id = z.pracownikodrejestracji
			left outer join kanaly k on k.id = pr.kanalinternetowy
		where w.Zatwierdzone between addHour(current_timestamp, -24) and current_timestamp and k.symbol = ? and wy.ukryty = 0 and w.platne ='1'
		and (
			(N.krytycznyPonizej is not null and N.krytycznyPowyzej is not null and wy.WynikLiczbowy not between N.krytycznyPonizej and N.krytycznyPowyzej)
			or (N.krytycznyPonizej is not null and N.krytycznyPowyzej is null and wy.WynikLiczbowy < N.krytycznyPonizej)
			or (N.krytycznyPonizej is null and N.krytycznyPowyzej is not null and wy.WynikLiczbowy > N.krytycznyPowyzej)
		) and p.symbol not in ('MCH', 'MCHC', 'LIC%')
		group by z.datarejestracji, z.numer, z.kodkreskowy, o.nazwa, pa.Nazwisko, pa.Imiona, pa.telefon, pa.Pesel
		order by o.nazwa, z.datarejestracji, z.numer;
"""

SQL_WERYFIKACJA = """
    select w.datarejestracji as DATA, z.numer as NUMER, o.nazwa as PPOBRAN,
		(pa.Nazwisko || ' ' || pa.Imiona) as PACJENT, 
		coalesce(cast(pa.PESEL as varchar(12)),'') as PESEL, pa.telefon as TELEFON,
		b.symbol as BADANIE,
		z.kodkreskowy as KOD,
		coalesce(cast(pa.PESEL as varchar(12)),'') as PESEL
		from wykonania w
			left outer join zlecenia z on z.id=w.zlecenie
			left outer join pacjenci pa on pa.id=z.pacjent
			left outer join oddzialy o on o.id=z.oddzial
			left outer join platnicy p on p.id=w.platnik
			left outer join badania b on b.id=w.badanie
			left outer join pracownicy pr on pr.id = z.pracownikodrejestracji
			left outer join kanaly k on k.id = pr.kanalinternetowy
		where
			 w.pozamknieciu ='0' and w.GODZINAREJESTRACJI between addHour(current_timestamp, -24) 
			 and current_timestamp and b.symbol in ('HIV-WB', 'KONSHCV', 'FTA', 'HBS-CON', 'KONSRCK') 
			 and k.symbol = ? and w.anulowane is null and w.platne ='1'
		order by o.nazwa, w.datarejestracji, z.numer;
"""

SQL_NIETERMINOWE = """
    select W.DataRejestracji as DATA, Z.Numer as NUMER, o.nazwa as PPOBRAN,
		(pa.Nazwisko || ' ' || pa.Imiona) as PACJENT, pa.telefon as TELEFON,
		coalesce(cast(pa.PESEL as varchar(12)),'') as PESEL,
		min(B.CzasMaksymalny/24) as MAXI,
		z.kodkreskowy as KOD,
		cast(list(trim(b.symbol), ' ') as varchar(200)) as BADANIA
		from Wykonania W
			left outer join Badania B on B.ID = W.Badanie
			left outer join Zlecenia Z on Z.ID = W.Zlecenie
			left outer join oddzialy o on o.id=z.oddzial
			left outer join Pacjenci Pa on Z.Pacjent = Pa.Id
			left outer join pracownicy pr on pr.id = z.pracownikodrejestracji
			left outer join kanaly k on k.id = pr.kanalinternetowy
		where W.PoZamknieciu = 0 and W.PoDystrybucji = 1 and k.symbol = ? and B.CzasMaksymalny > 20 
		and W.Anulowane is null and W.Zatwierdzone is null and AddHour(W.Dystrybucja, B.CzasMaksymalny*0.8) <= current_timestamp
		group by W.DataRejestracji, Z.Numer, o.nazwa, Pa.Nazwisko, Pa.Imiona, Pa.PESEL, pa.telefon, z.kodkreskowy
		order by W.DataRejestracji, Z.Numer;
"""


def generate_barcode_img_tag(barcode):
    barcode_image = code128.image(barcode)
    buff = io.BytesIO()
    barcode_image.save(buff, format='PNG')
    return '<img src="data:image/png;base64,%s">' % b64encode(buff.getvalue()).decode()


class RaportPunktPobran:
    def __init__(self, symbol, nazwa, adres, alias):
        czas = datetime.datetime.now()
        self.symbol = symbol
        self.nazwa = nazwa
        self.adres = adres
        self.alias = alias
        self.db_source = self.get_db_source()
        self.filename = "%s_%s_%s.pdf" % ("PunktPobran", self.symbol, czas.strftime("%d-%m-%Y_%H%M%S"))

    def get_db_source(self):
        if ':' in self.alias:
            splited = self.alias.split(':')
            self.alias = splited[-1]
            if 'pg' == splited[0]:
                return 'postgres'
        return 'firebird'

    def generuj(self):
        self.html = """<html><head>
        <style type="text/css">
        html, body {
            font-size: 10pt;
            font-family: 'Arial', helvetica, sans-serif;
            margin: 0; padding: 0;
        }
        @media print {
            @page { size: 210mm 297mm; margin: 10mm 10mm }
        }
        img#head {
            width: 40%            
        }
        div.titlebox {
            text-align: center;
            background: #eee;
            border: 1px solid #000;
            padding: 3pt;
        }
        div.titlebox_right {
            width: 55%;
            text-align: right;
            float: right;
        }
        div.informujemy {
            text-align: center;
            background: #eee;
            padding: 3pt;
            font-weight: bold;
            margin-top: 5pt;
            margin-bottom: 5pt;
        }
        div.informujemy_white {
            text-align: center;
            padding: 3pt;
            font-weight: bold;
            margin-top: 5pt;
            margin-bottom: 5pt;
        }

        table, table td, table th {
            border: 1px solid #000;
            border-collapse: collapse;
            font-size: 8pt;
        }

        table th {
            background: #ddd;
            text-align: center;
            font-weight: normal;
        }

        table img {
            width: 3cm !important;
            height: 0.5cm !important;
            margin: 0;
            padding: 0;
        }

        td.c {
            text-align: center;
        }

        div.niezgodnosc {
            border-bottom: 1px dashed #000;
            margin-bottom: 3pt;
            padding-bottom: 3pt;
        }

        </style></head>
            <body><img id="head" src="data:image/png;base64,""" + LOGO + """" />
            <div class="titlebox_right">""" + self.nazwa + """<br />
            Wygenerowano: """ + datetime.datetime.now().strftime("%Y-%m-%d %H:%M") + """</div>
        """
        self.zbierz_problemy()
        self.generuj_brak_materialu()
        self.generuj_bledy()
        self.generuj_krytyczne()
        self.generuj_weryfikacja()
        self.generuj_nieterminowe()

        self.html += "</body></html>"

    def zbierz_problemy(self):
        self.braki_materialu = []
        self.bledy = []
        self.krytyczne = []
        self.weryfikacja = []
        self.nieterminowe = []
        self.podsumowanie_mail = []
        cm = CentrumManager(adres=self.adres, alias=self.alias,
                            engine=self.db_source)
        c = cm.get_connection()
        with c.connection() as conn:
            sql = SQL_BRAKI_BLEDY
            sql_pg = sql.replace("addHour(current_timestamp, -24)", "(current_timestamp - interval '24 hours')")
            sql_pg = sql_pg.replace('?', '%s').replace("list(trim(b.symbol), ' ')",
                                                       "array_to_string(array_agg(trim(b.symbol)), ' ')")
            for row in conn.raport_slownikowy(sql, [self.symbol], sql_pg=sql_pg):
                if row['blad_symbol'] is None or row['blad_symbol'] == 'ZLEC':
                    self.braki_materialu.append(row)
                else:
                    self.bledy.append(row)
            sql = SQL_KRYTYCZNE
            sql_pg = sql.replace("addHour(current_timestamp, -24)",
                                 "(current_timestamp - interval '24 hours')").replace('%', '%%')
            sql_pg = sql_pg.replace('?', '%s').replace("list(trim(b.symbol), ' ')",
                                                       "array_to_string(array_agg(trim(b.symbol)), ' ')")
            for row in conn.raport_slownikowy(sql, [self.symbol], sql_pg=sql_pg):
                self.krytyczne.append(row)
            sql = SQL_WERYFIKACJA
            sql_pg = sql.replace("addHour(current_timestamp, -24)", "(current_timestamp - interval '24 hours')")
            sql_pg = sql_pg.replace('?', '%s').replace("list(trim(b.symbol), ' ')",
                                                       "array_to_string(array_agg(trim(b.symbol)), ' ')")
            for row in conn.raport_slownikowy(sql, [self.symbol], sql_pg=sql_pg):
                self.weryfikacja.append(row)
            sql = SQL_NIETERMINOWE
            sql_pg = sql.replace("addHour(current_timestamp, -24)", "(current_timestamp - interval '24 hours')")
            sql_pg = sql_pg.replace('?', '%s').replace("list(trim(b.symbol), ' ')",
                                                       "array_to_string(array_agg(trim(b.symbol)), ' ')")
            sql_pg = sql_pg.replace("AddHour(W.Dystrybucja, B.CzasMaksymalny*0.8)",
                                    "W.Dystrybucja + (B.CzasMaksymalny * 0.8 * (interval '1 hour'))")
            for row in conn.raport_slownikowy(sql, [self.symbol], sql_pg=sql_pg):
                self.nieterminowe.append(row)

    def generuj_brak_materialu(self):
        if len(self.braki_materialu) > 0:
            self.podsumowanie_mail.append('%d x brak materiału' % len(self.braki_materialu))
            self.html += """<div class="informujemy_white">Uprzejmie informujemy Państwa, że w dniu wczorajszym nie został przyjęty do realizacji materiał następujących pacjentów:</div>"""
            self.html += """<table><tbody><tr><th>Data i nr zlecenia</th><th>Kod kreskowy</th><th>Zleceniodawca</th>
                                <th>Pacjent</th><th>Badania i materiał</th></tr>"""
            for row in self.braki_materialu:
                kod_kreskowy = generate_barcode_img_tag(row['kod'])
                kod_kreskowy += '<br /><span style="font-size: 0.7em;">%s</span>' % row['kod']

                wiersz = """<tr><td class="c">%s<br />%d</td><td class="c">%s</td><td class="c">%s</td>
                    <td>%s<br />tel. %s</td><td>%s, %s</td></tr>"""
                wiersz %= (row['data'].strftime('%Y-%m-%d'), row['numer'],
                           kod_kreskowy,
                           row['ppobran'],
                           row['pacjent'], row['telefon'],
                           row['badania'], row['material'])
                self.html += wiersz
            self.html += "</tbody></table>"
        else:
            self.html += """<div class="informujemy_white">Uprzejmie informujemy Państwa, że w dniu wczorajszym nie stwierdziliśmy brakujących materiałów do zleceń nadesłanych z Państwa placówek</div>"""

    def generuj_bledy(self):
        if len(self.bledy) > 0:
            self.podsumowanie_mail.append('%d x błąd wykonania' % len(self.bledy))
            self.html += """<div class="informujemy_white">Dodatkowo informujemy Państwa, że w dniu wczorajszym odnotowaliśmy następujące niezgodności:</div>"""
            self.html += """<table><tbody><tr><th>Data i nr zlecenia</th><th>Kod kreskowy</th><th>Zleceniodawca</th>
                                <th>Pacjent</th><th>Badania i materiał</th><th>Nazwa niezgodności</th></tr>"""
            for row in self.bledy:
                kod_kreskowy = generate_barcode_img_tag(row['kod'])
                kod_kreskowy += '<br /><span style="font-size: 0.7em;">%s</span>' % row['kod']

                wiersz = """<tr><td class="c">%s<br />%d</td><td class="c">%s</td><td class="c">%s</td>
                    <td>%s<br />tel. %s</td><td>%s, %s</td><td class="c">%s</td></tr>"""
                wiersz %= (row['data'].strftime('%Y-%m-%d'), row['numer'],
                           kod_kreskowy,
                           row['ppobran'],
                           row['pacjent'], row['telefon'],
                           row['badania'], row['material'], row['blad'])
                self.html += wiersz
            self.html += "</tbody></table>"
        else:
            self.html += """<div class="informujemy_white">Dodatkowo informujemy Państwa, że w dniu wczorajszym nie stwierdziliśmy niezgodności</div>"""

    def generuj_krytyczne(self):
        if len(self.krytyczne) > 0:
            self.podsumowanie_mail.append('%d x wyniki krytyczne' % len(self.krytyczne))
            self.html += """<div class="informujemy_white">Dodatkowo informujemy Państwa, że w dniu wczorajszym odnotowaliśmy krytyczne wartości wyników badań:</div>"""
            self.html += """<table><tbody><tr><th>Data i nr zlecenia</th><th>Kod kreskowy</th><th>Zleceniodawca</th>
                                <th>Pacjent</th><th>Badania</th></tr>"""
            for row in self.krytyczne:
                kod_kreskowy = generate_barcode_img_tag(row['kod'])
                kod_kreskowy += '<br /><span style="font-size: 0.7em;">%s</span>' % row['kod']

                wiersz = """<tr><td class="c">%s<br />%d</td><td class="c">%s</td><td class="c">%s</td>
                    <td>%s<br />tel. %s</td><td>%s</td></tr>"""
                wiersz %= (row['data'].strftime('%Y-%m-%d'), row['numer'],
                           kod_kreskowy,
                           row['ppobran'],
                           row['pacjent'], row['telefon'],
                           row['badania'])
                self.html += wiersz
            self.html += "</tbody></table>"
        else:
            self.html += """<div class="informujemy_white">Dodatkowo informujemy Państwa, że w dniu wczorajszym nie odnotowaliśmy krytycznych wartości wyników badań.</div>"""

    def generuj_weryfikacja(self):
        if len(self.weryfikacja) > 0:
            self.podsumowanie_mail.append('%d x wyniki krytyczne' % len(self.weryfikacja))
            self.html += """<div class="informujemy_white">Dodatkowo informujemy Państwa, że w dniu wczorajszym odnotowaliśmy wyniki badań, które wymagają dalszej weryfikacji przez laboratorium:</div>"""
            self.html += """<table><tbody><tr><th>Data i nr zlecenia</th><th>Kod kreskowy</th><th>Zleceniodawca</th>
                                <th>Pacjent</th><th>Badanie</th></tr>"""
            for row in self.weryfikacja:
                kod_kreskowy = generate_barcode_img_tag(row['kod'])
                kod_kreskowy += '<br /><span style="font-size: 0.7em;">%s</span>' % row['kod']
                row['badanie'] = (row['badanie'] or '').strip()
                row['badanie'] = {
                    'FTA': 'WR', 'HIV-WB': 'HIV', 'HIV-PCR': 'HIV', 'KONSHCV': 'HCV',
                    'HBS-CON': 'HBS', 'KONSRCK': 'GRUPA',
                }.get(row['badanie'], row['badanie'])
                wiersz = """<tr><td class="c">%s<br />%d</td><td class="c">%s</td><td class="c">%s</td>
                    <td>%s<br />tel. %s</td><td>%s</td></tr>"""
                wiersz %= (row['data'].strftime('%Y-%m-%d'), row['numer'],
                           kod_kreskowy,
                           row['ppobran'],
                           row['pacjent'], row['telefon'],
                           row['badanie'])
                self.html += wiersz
            self.html += "</tbody></table>"
        else:
            self.html += """<div class="informujemy_white">Dodatkowo informujemy Państwa, że w dniu wczorajszym nie odnotowaliśmy wyników badań, które wymagają dalszej weryfikacji przez laboratorium.</div>"""

    def generuj_nieterminowe(self):
        if len(self.nieterminowe) > 0:
            self.podsumowanie_mail.append('%d x niedotrzymany termin wykonania' % len(self.nieterminowe))
            self.html += """<div class="informujemy_white">Dodatkowo informujemy Państwa, że w dniu wczorajszym zostały przekroczone czasy wykonania badań:</div>"""
            self.html += """<table><tbody><tr><th>Data i nr zlecenia</th><th>Kod kreskowy</th><th>Zleceniodawca</th>
                                <th>Pacjent</th><th>Badania</th><th>Czas max</th></tr>"""
            for row in self.nieterminowe:
                kod_kreskowy = generate_barcode_img_tag(row['kod'])
                kod_kreskowy += '<br /><span style="font-size: 0.7em;">%s</span>' % row['kod']

                wiersz = """<tr><td class="c">%s<br />%d</td><td class="c">%s</td><td class="c">%s</td>
                    <td>%s<br />tel. %s</td><td>%s</td><td>%s</td></tr>"""
                wiersz %= (row['data'].strftime('%Y-%m-%d'), row['numer'],
                           kod_kreskowy,
                           row['ppobran'],
                           row['pacjent'], row['telefon'],
                           row['badania'], str(row['maxi']))
                self.html += wiersz
            self.html += "</tbody></table>"
        else:
            self.html += """<div class="informujemy_white">Dodatkowo informujemy Państwa, że w dniu wczorajszym nie zostały przekroczone czasy wykonania badań</div>"""

    def zapisz(self):
        pdf = weasyprint.HTML(string=self.html)
        pdf.write_pdf(self.filename)

    def wyslij(self, adresy):
        temat = 'Raport z niewykonanych badań - %s' % self.nazwa
        if len(self.podsumowanie_mail) > 0:
            tresc = "Proszę otworzyć załączony plik.\nWykryte nieprawidłowości:\n" + "\n".join(self.podsumowanie_mail)
        else:
            tresc = "Brak nieprawidłowości"
        sender = Email()
        adresy = adresy.strip()
        try:
            sender.log_save(self.filename.replace('.pdf', '.email'), adresy.split(' '), temat, tresc, [self.filename])
            sender.send(adresy.split(' '), temat, tresc, [self.filename])
        except Exception as e:
            sentry_sdk.capture_exception(e)
            sender.send(adresy.split(' '), temat, tresc, [self.filename], enqueue=True)
            time.sleep(30)
            sender.send_all_from_queue()



if __name__ == '__main__':
    symbol = sys.argv[1]
    nazwa = sys.argv[2]
    adres = sys.argv[3]
    alias = sys.argv[4]
    adresy = sys.argv[5]
    rbp = RaportPunktPobran(symbol, nazwa, adres, alias)
    rbp.generuj()
    rbp.zapisz()
    rbp.wyslij(adresy)
