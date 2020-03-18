# Office Hours Chat Bot

##Heroku Deploy

1. Copy `heroku.env.sample` to `heroku.env` and add in all the config options.
2. Run `heroku config:set $(cat heroku.env)`
3. Run `heroku addons:create mongolab:sandbox`
4. Run `heroku ps:scale bot=1`
3. Use Heroku normally.

## Local Development
1. Create a copy of `sample-prop.json` called 'prop.json' and put in your values.
2. `python3 bot.py`

#Remember not to version private keys!