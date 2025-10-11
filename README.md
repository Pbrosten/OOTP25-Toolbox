# OOTP25-Toolbox
This project provides a set of tools, analytics, and projections to assist in data driven decision making in OOTP 25.

## Description
This project was heavily inspired by the [OOTP Calculator App](http://www.ootpcalculator.com). After spending many hours using that phenomenal tool, I started to ask: "What analytics would be most useful for driving data-informed decisions in OOTP?"

This toolbox hopes to provide a one-stop shop for any data and analytics a GM would want in an OOTP franchise. Current functionalities include:

- Player Search – Find players across the league.

- Player Projection System (Batters) – Forecast batter performance based on current offensive ratings.

- Player Run Value Predictor (Batters) – Estimate expected offensive contributions.

- Player Profiles – Visualize player expected performance relative to league and position cohorts.

## Installation
This app is run using the `docker-compose.yml`. There are some configuration steps needed before the app can fully run.
### Set OOTP25 Dump Files
The OOTP25 Toolbox relies on parsing OOTP dump files. Both the yearly and monthly dump files are expected as MySQL files. In order to configure the OOTP dump files do the following:

1. Open your OOTP25 game file.
2. Select **Game** > Almanac > Almanac Options ...
3. Check **Monthly data dump to MySQL file**. Then select **Edit Profile** and make sure that `players_batting`, `players_fielding`, and `players_pitching` are checked.
4. Repeat for **Yearly data dump to MySQL file**. In the profile, ensure `players_basic`, `teams`, and `players_career_batting_stats` are checked.

Your OOTP dump files will be found in the OOTP25 `saved_games/{save_name}/dump` folder.

> **Note**: Before using the application, ensure at least one `yearly` dump is in the folder and delete all prior `monthly` files. This is in order to optimize OOTP dump wait time while playing.

### Connect the Toolbox to the Dump Files
Copy the `.env-template` file from the `backend/template/` folder. Move this template into the `backend/` directory, rename it `.env`. Set `GAME_PATH` as the path to the OOTP 25 saved_game file and the `GAME_STATE` as the save file name.

This will give the app all the information needed to connect the appropriate dump files.

### Create Backend Virtual Environment
Enter the `backend/` directory. This project used `uv` as its python package manager. Take a quick look at the [uv documentation](https://docs.astral.sh/uv/getting-started/) if you are unfamiliar with the package manager.

Once `uv` is installed, run `uv venv`.

## Usage
### Update the Database
In order to update the app database, activate `backend/.venv` Then run one of the following options
#### 1. Run from OOTP25-Toolbox dir
Run `flask --app backend/app init-db` followed by `flask --app backend/app update-db`

#### 2. Run from OOTP25-Toolbox/backend dir
Run `flask --app app init-db` followed by `flask --app app update-db`

Once the migrations are complete the app is ready for use.

### Run the App
To run the OOTP25-Toolbox app simply run `docker-compose up --build` from the OOTP25-Toolbox dir.

Once running the app will be accessable at the following urls:

- Backend: `localhost:5000`
- App UI: `localhost:5173`
