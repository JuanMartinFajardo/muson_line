readme.txt

# How to run the python server

By default it is hosted in port 5001

1. Clone the repository
2. Create a virtual enviroment: `virtualenv .musenv`
3. Activate the enviroment: `source .musenv/bin/activate`
4. Install the requirements: `pip install -r requirements.txt`
5. Run the server: `python3 server.py`


To run it locally and make test, I personally use ngrok.
1. Download and configure ngrok
2. Get your server running on your computer `ngrok http 5001`.


# How to train the bot
1. Execute `python3 global_trainer.py`

