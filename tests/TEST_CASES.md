# Use cases and UI test cases

Who uses this: one household sharing money. Typically two adults, sometimes more people, on a
laptop at home and on phones on the same Wi-Fi. There are no logins. Anyone on the home network
can open and change the page.

What they come to do:

1. **Glance.** "How much do we have, and how much of it is really free?" (Overview)
2. **Record.** Add, fix or remove a payment by hand, or bring in a bank statement. (Payments)
3. **Stay ahead of bills.** See what is due, tick it off when paid. (Bills)
4. **Hold a line.** Set monthly budgets and see which are running hot. (Budgets)
5. **Save towards things.** Keep pots and move money into them. (Pots)
6. **Understand.** See patterns: which days, which categories, needs against wants. (Insights)
7. **Share fairly.** See who spent what. (Household)
8. **Use real numbers.** Link a bank, choose which accounts count, export or back up. (Accounts)
9. **Make it theirs.** Name, currency, people, theme, and clearing the example data. (Settings)

Every case below is automated. `UI` cases are in `tests/test_ui.py` (the test name starts with the
case id). `API` cases are in `tests/test_api.py`. All run against a throwaway server with the date
pinned to Thursday 12 November 2026, so the example figures are the same on every run.

## Overview

| Id | Flow | Expected |
|---|---|---|
| OV01 | Open the page for the first time | Greeting, date and month show. Balance is in dollars and equals opening balance plus all payments. Example-data notice is visible. All seven cards and the chart render. Latest payments shows six rows. |
| OV02 | Read "Safe to spend" | Equals balance minus bills not yet paid this month. Shows days left in the month. |
| OV03 | Read the forecast | Month-end figure equals balance plus paydays and minus bills still to come. One marker per upcoming bill or payday. |
| OV04 | Switch Quarter / 6 months / Year | 3, 6 or 12 month columns. The chosen button is marked pressed. |
| OV05 | Page through "Noticed" | Counter moves from 1 to 2, the text changes, and its link opens the related page. |
| OV06 | Open with no data at all | Balance is $0, no example notice, every card explains what to add. No errors. |

## Navigation and layout

| Id | Flow | Expected |
|---|---|---|
| NAV01 | Click each sidebar item | Heading changes, the item is marked current, the address ends in `#page`. |
| NAV02 | Open a link that names a page | `/#bills` opens Bills. An unknown name opens the Overview. |
| NAV03 | Previous and next month | Label changes. Past months say "Looking back", show the end-of-month balance and offer no Pay buttons. Next is disabled on the current month. |
| NAV04 | Phone width (375 px) | Pages become a bottom bar. The sidebar balance is hidden. No page scrolls sideways. |
| NAV05 | Theme button | Cycles device → light → dark. The choice survives a reload. |

## Payments

| Id | Flow | Expected |
|---|---|---|
| PAY01 | Add money out | Toast confirms. Balance drops by the amount. Row shows "Today", category and person. Stored exactly as entered. |
| PAY02 | Add money in | Balance rises. Row shows a plus sign and "Income". |
| PAY03 | Submit with no amount | The form stays open. Nothing is stored. Cancel closes it. |
| PAY04 | Edit a payment and tick "Always use this category" | Row shows the new category. A rule is stored and listed under Accounts → Your data, where it can be forgotten. |
| PAY05 | Focus a row and press Enter | The edit form opens. |
| PAY06 | Delete, then Undo | Row disappears and the count drops, then both come back. |
| PAY07 | Search and filter by category | List and totals narrow as you type. The box keeps focus. No match shows "No payments match". |
| PAY08 | Enter HTML as a description | Shown as plain text. Nothing runs. |
| PAY09 | Import a CSV statement | Preview shows how many are new, the columns used and guessed categories. Importing adds them. Importing the same file again adds nothing and the button is disabled. |
| PAY10 | Import a card statement where spending is positive | Ticking "Amounts are reversed" flips the preview, and the import stores negatives. |
| PAY11 | Import a file with no date column | A toast explains what is missing. Nothing is stored. |
| PAY12 | Export | Downloads `payments.csv`. |

## Bills

| Id | Flow | Expected |
|---|---|---|
| BILL01 | Pay a bill | Row says "paid" and loses its button. A payment dated today is stored. Safe to spend does not change, because the bill was already set aside. |
| BILL02 | Mark a payday received | Balance rises by the paycheck. |
| BILL03 | Add a bill, remove it, undo | Appears with "in N days", disappears, comes back. |
| BILL04 | A bill whose day has passed unpaid | Flagged "Overdue". |

## Budgets, pots, household

| Id | Flow | Expected |
|---|---|---|
| BUD01 | Set and clear budgets in Settings | A category over its budget shows "Over" on Budgets and on the Overview. A cleared budget shows "no budget". |
| POT01 | Create a pot, add money until full | Progress updates, "Full" appears, balance drops, and a Savings payment is recorded. |
| POT02 | Remove a pot | It disappears, with an undo. |
| HOUSE01 | Open Household | One row per person plus Shared, with what each brought in and spent. |

## Insights

| Id | Flow | Expected |
|---|---|---|
| INS01 | Open Insights | A cell for every day of the month, future days dimmed. Needs / wants / saved against the 50 / 30 / 20 guide. Category table. Biggest payments, largest first. |

## Settings and example data

| Id | Flow | Expected |
|---|---|---|
| SET01 | Change name, currency and people | Sidebar title changes, amounts use the new currency, the "Who" list offers the new names. |
| SET02 | Clear examples | Asks first. "Keep them" changes nothing. Confirming removes every example, hides the notice and keeps the chosen currency. |
| SET03 | Clear examples after adding your own payment | Only the examples go. |

## Accounts and bank

| Id | Flow | Expected |
|---|---|---|
| BANK01 | Paste a setup token and connect | Accounts are listed with their bank. The balance becomes the sum of account balances. Fetched payments show their account and a guessed category. |
| BANK02 | Untick an account | Its balance and payments leave the totals. |
| BANK03 | Empty token, bad token, sync too soon, disconnect | Each gets a plain message. Disconnect asks first and deletes the stored key. |
| DATA01 | Download a backup | Downloads `finance-backup.json`. |

## Resilience

| Id | Flow | Expected |
|---|---|---|
| NET01 | A change is made from another device | It appears within a few seconds, without reloading. |
| NET02 | The server stops, then returns | A notice says it cannot be reached. Saving says nothing was saved. The notice clears on its own when the server is back. |

## Server (API) cases

| Test | What it proves |
|---|---|
| `test_first_run_creates_usd_example_data` | First run writes example data in USD, flagged as examples, none dated in the future. |
| `test_empty_flag_starts_with_nothing` | `--empty` starts clean. |
| `test_serves_only_the_public_files` | Only `public/` is served. The data file and source cannot be fetched. |
| `test_create_update_delete_and_file_on_disk` | Changes reach `data.json`. |
| `test_data_survives_a_restart` | Data is still there after a restart. |
| `test_rejects_bad_requests` | Unknown collections, bad ids and non-object bodies are refused. |
| `test_other_websites_cannot_write` | A page on another site cannot change anything. |
| `test_batch_applies_all_writes` | Several changes in one request. |
| `test_csv_*` | Statement parsing: single amount column, separate in and out columns, reversed signs, parentheses, unreadable rows, duplicates, missing header. |
| `test_remembered_rule_wins_on_import` | A remembered category beats the built-in guess. |
| `test_export_and_backup` | CSV export and JSON backup contents. |
| `test_bank_connect_sync_and_secret_stays_on_server` | Token exchange, account and payment import, pending items skipped, the access key never returned to the browser and stored owner-only, rate limit, disconnect. |
| `test_bank_edits_survive_a_resync` | Your category and person edits are kept when the bank is synced again. |
| `test_bank_bad_or_used_token` | Bad and already-used tokens are explained. |

## Not covered

- A real bank bridge. Bank tests use a stand-in that follows the published SimpleFIN protocol.
- Announcing the `.local` name on the network (it needs a real network and other devices).
- Browsers other than Chromium.
- The look of the page. Tests check content and behaviour, not pixels.
