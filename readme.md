
# CallMus
CallMus is an online app to play the 2 player version of the Spanish card game Mus.

In this readme you will find:

1. An overview of the project CallMus
2. How to set up the server
3. How the bot is trained
4. The rules of Mus
5. A few words on the game


# 1. What is CallMus?

CallMus is intended to be a simple but robust online plataform to play the two player version of Mus. The app offers so far two modes: **online** playing and playing **against a bot**.
To play online one can press **Create new game** and get a code. To play with someone, just send him/her the code. If **Public game** is activated, it will appear in a list of public games, from where other players can join.

The game is offered in Spanish and English.

I included an **account system** to keep track of the winings. When played logged, the matches contribute to compute an **ELO ranking** among players.


# 2. How to run the python server?

By default it is hosted in port 5001

1. Clone the repository
2. Create a virtual enviroment: `virtualenv .musenv`
3. Activate the enviroment: `source .musenv/bin/activate`
4. Install the requirements: `pip install -r requirements.txt`
5. Run the server: `python3 server.py`


To run it locally and make tests, I personally use ngrok.
1. Download and configure ngrok
2. Get your server running on your computer `ngrok http 5001`.






# 3. How does the bot learn to play Mus?

The bot "intelligence" consists on three parts.
1. A model for deciding **whether to discard or not** (Mus vs no Mus)
2. A model to decide **which cards to discard** in case of mus.
3. A model to handel the **bettings**.
 

For the sake of the training, **every game generates a log** that is stored in the folder `logs` as a .jsonl file. 
Each line records all the data regarding a single turn: which cards players had, who's turn was, what action it took place, what was the bet called so far, how many points each player had, and who eventually won the round, among others.

To make the models more efficient, we developed a python script to count the **probability of winning** each round with given cards (`lean/probability_calculator.py`). We give the model these derived variables as an extra input to make the learning more based on rationality.


1. The Mus/no Mus model is trained using a **random forest** to read these lines (actually, only the ones corresponding to turns of the winner) and predict an output: **Mus/no Mus**
2. The card discarding model is trained as well using a **random forest** algorithm to learn from the discards of the winners. In this case the output generated is a **binary number from 1 to 16** (as there are 16 possible discards). As discarding the first and the second card from 4,5,10,2 (discard code 1100) is the same as discarding the third and the fourth from 10,2,4,5 ( discard code 0011), we sort the cards increasingly.
3. The betting model is trained in the same fashion usind a **random forest** algorithm to decide between the **options** (bid, fold, raise, ordago) depending on the case. 

To train it, execute `python3 global_trainer.py`.


Performance so far:
1. The first model shows a really **good performance**. Basically, it learnt what hands are good enough to keep. The test showed a $90%$ of accuracy (with respect to human decisions)
2. The second model **works fine** as well. It learnt how to improve a hand by throwing the right cards. The accuracy was around $70%$
3. The third model is **not good enough**. It can play, but it is extremely cautious and almost never raises the bet. Basically, with this model, it learnt how to play 'statistically' like the players. In Mus for two, players are usually cauitous and what determines the edge is the **ability to bluff at the right time**. As there is no possible way to imitate this globally, players must learn in each game how to bluff the particular opponent. I am seeking another model that can achieve this goal better. Accuracy respect to human decisions (imitating) is of $65%$. The number is not good and the play-like-human criteria is not even a good test.

To sum up, learning to imitate is a good strategy for the first two models, but not for the third.


# 4. The Rules of Mus (for 2 people)


Mus is a classic Spanish card game traditionally played in partnerships, but the two-player variant offers a fast-paced, psychological duel. This version emphasizes bluffing and tactical betting.

## 4.1. The Basics
* **The Deck:** If you use the Spanish deck, the used cards are 1 (Ace),2, 3, 4, 5, 6, 7, 10 (Sota), 11 (Caballo), 12 (Rey). If you use a Poker one: 1, 2, 3, 4, 5, 6, 7, Jack, Queen, King.
* **Special Card Values:** * **3s** are considered **Kings**.
    * **2s** are considered **Aces**.
    * This means there are effectively 8 Kings and 8 Aces in the deck.
* **Winning:** The game is played to **40 points**.

## 4.2. The Deal and "Mus"
1.  Each player is dealt **4 cards**.
2.  The non-dealer (**Postre**) speaks first. They can say **"Mus"** (if they want to discard and draw new cards) or **"No Mus"** (to start the betting rounds immediately).
3.  **If both say "Mus":** Both players discard any number of cards and receive replacements from the dealer. This continues until one player says "No Mus."
4.  **If one says "No Mus":** The discarding phase ends, and the betting begins.

## 4.3. The Four Lances (Phases)
In every hand, players compete in four distinct categories. Betting happens in each category before moving to the next.

### I. Grande (High)
* **Goal:** Have the highest cards.
* **Hierarchy:** King/3, Knight, Jack, 7, 6, 5, 4, Ace/2.
* The best hand is four Kings.

### II. Chica (Low)
* **Goal:** Have the lowest cards.
* **Hierarchy:** Ace/2, 4, 5, 6, 7, Jack, Knight, King/3.
* The best hand is four Aces.

### III. Pares (Pairs)
* Before betting, players must declare if they have any pairs by saying **"Pares sí"** or **"Pares no."** * If both have pairs, they bet.
* **Types of Pairs:**
    * **Par (Pair):** Two cards of the same value.
    * **Medias (Three-of-a-kind):** Three cards of the same value.
    * **Duples (Two pairs or Four-of-a-kind):** Highly valuable.

### IV. Juego (Game)
* Players add the values of their cards: Kings/3s/Knights/Jacks = 10; others = face value; Aces/2s = 1.
* You have **"Juego"** if your total is **31 or more**.
* **Hierarchy:** 31 is the best, then 40, 37, 36, 35, 34, 33, and 32.
* **Punto:** If neither player has 31 or more, they bet on who is closest to 31 (this is called "Punto").

## 4.4. Betting Mechanics
In any round, a player can:
* **Pass:** Move to the next round without betting.
* **Envido (Bid):** Offer a bet (minimum 2 points).
* **Veo (I call):** The winner is determined at the end of the hand.
* **No veo (I fold):** The player who bet takes 1 point immediately, and the round ends.
* **Subo (I raise):** The player can raise the the bet the other player bid.
* **Órdago:** A bet for the entire game. If accepted, cards are shown immediately to decide the winner of the whole match.

## 4.5. Scoring Table (End of Hand)
If a bet was accepted, the winner of that round takes the points. If everyone passed, the winner of the round takes "de paso" points at the end.

| Category | Points for Winner |
| :--- | :--- |
| **Grande / Chica** | 1 point (if passed) |
| **Par (Pair)** | 1 point |
| **Medias** | 2 points |
| **Duplex** | 3 points |
| **Juego (31)** | 3 points |
| **Juego (not 31)** | 2 points |
| **Punto** | 1 point |

## 4.6. Two-Player Strategy Tips
* **The Bluff:** Since there is no partner to worry about, bluffing is more frequent. You can bet "Grande" even with poor cards to force a "Fold"
* **The Órdago:** Use the *Órdago* cautiously. It is a powerful tool to stop an opponent who is about to reach the winning score.
* **Postre:** The dealer (Postre) has the advantage in a tie, as the non-dealer (Mano) wins ties in the showdown.


## 5. A few words about Mus