from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar

# Current date
today = datetime.today()

# Previous month
prev_month = today - relativedelta(months=1)

# First day of previous month
START_DATE = datetime(
    prev_month.year,
    prev_month.month,
    1
)

# Last day of previous month
last_day = calendar.monthrange(
    prev_month.year,
    prev_month.month
)[1]

END_DATE = datetime(
    prev_month.year,
    prev_month.month,
    last_day
)

print(
    "START_DATE:",
    START_DATE.strftime("%d-%b-%Y")
)

print(
    "END_DATE:",
    END_DATE.strftime("%d-%b-%Y")
)