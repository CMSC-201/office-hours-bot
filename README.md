# Office Hours Chat Bot

## Heroku Deploy

1. Copy `heroku.env.sample` to `heroku.env` and add in all the config options.
2. Run `heroku config:set $(cat heroku.env)`
3. Run `heroku addons:create mongolab:sandbox`
3. Do the first push, e.g. `git push heroku master`
4. Run `heroku ps:scale bot=1`
3. Use Heroku normally.

## Local Development
1. Create a copy of `sample-prop.json` called 'prop.json' and put in your values.
2. `python3 bot.py`

#Remember not to version private keys!

## Setup

You must have developer mode enabled on your Discord client in order to proceed.
1. Go to User Settings on your Discord Client
2. In the settings, go to Appearance
3. One of the options should be named Developer Mode, toggle it on.
4. You may now right click servers (guilds), channels, messages, and users and click Copy ID to get their Discord UID.
