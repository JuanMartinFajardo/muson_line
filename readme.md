Mus is a famous Spanish card game.

In this readme you will find


1. An overview of the project CallMus
2. How to set up the server
3. How the bot is trained
4. The rules of Mus
5. A few words on the game


# 1. What is CallMus?




# 2. How to run the python server?

By default it is hosted in port 5001

1. Clone the repository
2. Create a virtual enviroment: `virtualenv .musenv`
3. Activate the enviroment: `source .musenv/bin/activate`
4. Install the requirements: `pip install -r requirements.txt`
5. Run the server: `python3 server.py`


To run it locally and make test, I personally use ngrok.
1. Download and configure ngrok
2. Get your server running on your computer `ngrok http 5001`.






# 3. How does the bot learn to play Mus?

The bot "intelligence" consists on three parts.
1. A model for deciding whether to mus or not
2. A model to decide what cards to discard in case of mus.
3. A model to handel the bettings.
 

For the sake of the training, every game generates a log that is stored in the folder `logs` as a .jsonl file. 
Each line records all the data regarding a single turn: which cards players had, who's turn was, what action it took place, what was the bet called so far, how many points each player had, and who eventually won the round, among others.

To make the models more efficient, we developed a python script to count the probability of winning each round with given cards (`lean/probability_calculator.py`). We give the model these derived variables as an extra input to make the learning more based on rationality.


1. The Mus/no Mus model is trained using a random forest to read these lines (actually, only the ones corresponding to turns of the winner) and predict an output: Mus/no Mus
2. The card discarding model is trained as well using a random forest algorithm to learn from the discards of the winners. In this case the output generated is a binary number from 1 to 16 (as there are 16 possible discards). As discarding the first and the second card from 4,5,10,2 (discard code 1100) is the same as discarding the third and the fourth from 10,2,4,5 ( discard code 0011), we sort the cards increasingly.
3. The betting model is trained in the same fashion usind a random forest algorithm to decide between (bid, fold, raise, ordago) depending on the case. 

To train it, execute `python3 global_trainer.py`.


Performance so far:
1. The first model shows a really good performance. Basically, it learnt what hands are good enough to keep.
2. The second model works fine as well. It learnt how to improve a hand by throwing the right cards.
3. The third model is not good enough. It can play, but it is extremely cautious and almost never raises the bet. Basically, with this model, it learnt how to play 'statistically' like the players. In Mus for two, players are usually cauitous and what determines the edge is the ability to bluff at the right time. As there is no possible way to imitate this globally, players must learn in each game how to bluff the particular opponent. I am seeking another model that can achieve this goal better.

To sum up, learning to imitate is a good strategy for the first two models, but not for the third.


# 4. The Rules of Mus (for 2 people)


Mus is a classic Spanish card game traditionally played in partnerships, but the two-player variant offers a fast-paced, psychological duel. This version emphasizes bluffing and tactical betting.

## 1. The Basics
* **The Deck:** A standard 40-card Spanish deck (no 8s, 9s, or 10s).
* **Special Card Values:** * **3s** are considered **Kings**.
    * **2s** are considered **Aces**.
    * This means there are effectively 8 Kings and 8 Aces in the deck.
* **Winning:** The game is usually played to **30 or 40 points** (tracked with stones or beans called *amarrakos*).

## 2. The Deal and "Mus"
1.  Each player is dealt **4 cards**.
2.  The non-dealer speaks first. They can say **"Mus"** (if they want to discard and draw new cards) or **"No Mus"** (to start the betting rounds immediately).
3.  **If both say "Mus":** Both players discard any number of cards and receive replacements from the dealer. This continues until one player says "No Mus."
4.  **If one says "No Mus":** The discarding phase ends, and the betting begins.

## 3. The Four Lances (Rounds)
In every hand, players compete in four distinct categories. Betting happens in each category before moving to the next.

### I. Grande (Big)
* **Goal:** Have the highest cards.
* **Hierarchy:** King/3, Knight, Jack, 7, 6, 5, 4, Ace/2.
* The best hand is four Kings.

### II. Chica (Small)
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

## 4. Betting Mechanics
In any round, a player can:
* **Pass:** Move to the next round without betting.
* **Envido (Bet):** Offer a bet (minimum 2 points).
* **Veo (I accept):** The winner is determined at the end of the hand.
* **No veo (I decline):** The player who bet takes 1 point immediately, and the round ends.
* **Órdago:** A bet for the entire game. If accepted, cards are shown immediately to decide the winner of the whole match.

## 5. Scoring Table (End of Hand)
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

## 6. Two-Player Strategy Tips
* **The Bluff:** Since there is no partner to worry about, bluffing is more frequent. You can bet "Grande" even with poor cards to force a "Fold"
* **The Órdago:** Use the *Órdago* cautiously. It is a powerful tool to stop an opponent who is about to reach the winning score.
* **Postre:** The dealer (Postre) has the advantage in a tie, as the non-dealer (Mano) wins ties in the showdown.
