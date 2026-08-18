# PG Telegram Daily Sales — Android APK

This Android app runs two read-only PostgreSQL queries, fills the Daily Sales template, formats the Yesterday/MTD Telegram message, and posts it to selected groups or forum topics using a Telegram bot or user account.

## Build the APK with GitHub (no Android Studio)

1. Sign in to GitHub and create a new **private** repository.
2. Upload every file and folder from this project, including the hidden `.github` folder.
3. Open the repository's **Actions** tab.
4. Select **Build Android APK**.
5. Click **Run workflow**, then **Run workflow** again.
6. Wait for the green check mark.
7. Open the completed workflow run.
8. Under **Artifacts**, download `PGTelegramReporter-APK`.
9. Extract the artifact ZIP to obtain the `.apk`.
10. Copy the APK to Android and install it. Allow **Install unknown apps** if prompted.

## First use

1. Enter PostgreSQL host, port, database, read-only username/password, SSL mode, and the two queries.
2. Query 1 must return one Yesterday row; Query 2 must return one MTD row.
3. Both query rows must be: `Bet, Win, Hand, Gross, Profit`.
4. Configure Telegram bot mode or user mode.
5. In user mode, send the login code and log in, then use **Scan User Groups / Topics**.
6. Tap **Run Now** to test before enabling the daily service.
7. Enable secret saving, save settings, and start the daily service.
8. In Android settings, allow notifications and set battery usage to **Unrestricted**.

Do not put database passwords, Telegram tokens, API hashes, or session files in GitHub. Credentials are entered only after installation.
