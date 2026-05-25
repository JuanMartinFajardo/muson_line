
# CallMus
CallMus is an online app to play the 2 player version of the Spanish card game Mus.

In this readme you will find:

1. An overview of the project CallMus
2. How to set up the server
3. How the bot is trained
4. The rules of Mus
5. A few words on the game
6. References


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

## 3.1 First attemps

At the beginning I used a random forest method to decide upon the cards to do mus or not, and if so, which cards to discard. The result was not bad at all, but 

The bot "intelligence" consists on three parts.
1. A model for deciding **whether to discard or not** (Mus vs no Mus)
2. A model to decide **which cards to discard** in case of mus.
3. A model to handel the **bettings**.

For the sake of the training, **every game generates a log** that is stored in the folder `logs` as a .jsonl file. 
Each line records all the data regarding a single turn: which cards players had, who's turn was, what action it took place, what was the bet called so far, how many points each player had, and who eventually won the round, among others.

To make the models more efficient, I developed a python script to count the **probability of winning** each round with given cards (`lean/probability_calculator.py`). I give the model these derived variables as an extra input to make the learning more based on rationality.

All three models were trained using a random forest method. The first two performed well, whereas the third (betting system) was horrible, because it learned to imitate other players, not what a good hand is or where to bluff. So I decided to seek for other strategies.

## 3.2 Deep CFR

The Counterfactual Regret Minimization (CFR Minimization) algorithm consists roughly on moving randomly through the game tree and storing the regrets of each choide. Trying to minimize this regret, we would reach the Nash Equilibrium, that by applying it we can play 'deffensively': meaning that our expected value is $\geq 0$.
In general, this game tree is too large. In [1] the authors develope a model called Deep CFR that combines two neural networks (regret network and strategy network) to try to reach this nash equilibrium (stored in the strategy network). I implemented this model to approach the Nash Equilibrium. In particular I implemented the Linear CFR.

## 3.3. Implementation of the Deep CFR
Given my computing performance limitations, I use fine-tunning, to make the process faster.
Comment on reservoir sampling ...

The structure goes as follows. Fix a number of iterations (in our case 5000).
For each iteration we run 500 random games in the game situation tree, and for each one of them we explore the tree of posibilities with `transverse`. Then we train both networks using a Stochastic Gradient Descent.

The variables considered are:
- Who is Mano
- My cards (4 values)
- The phase (High, Low, Pair, Game)
- Last amount bet
- The bet called for each phase
- Who received the bet called (me, the opponen, or no one yet)
- My points
- The opponent's points
- The amount of mus rounds
- The amount of cards discarded by the opponent


## 3.4 Deciding Mus vs no Mus and discarding

In order to achieve good performance in the random game samplings, I replaced both the model for mus/no mus and the one for discards with optimized algorithms. Moreover, I decided that there is not a big choice to be made when deciding mus/no mus or which cards to discard. Obviously there are somehow strategic choices to be made here, but appart from some more or less influential percentage of bluffing, everyone agrees on what a good hand is. Therefore, I decided to desing an optimized method to decide if you want to discard and in that case which cards you would like to.


1. Mus no Mus: In order to decide if a hand is good or not, I computed for every hand all the probabilities of winning at each round (High, Low, Pair, Game), and I stored them in a learn/global_variables_mus_data.json. Luckly, for this game there are only 330 possible hands, so that is pretty lightweight. For every hand, the first 4 numbers correspond to the 4 probabilities of wining each round being Mano, and the following four are the same but without being Mano. With this probabilities computed, I decided to compute the expected value of each hand. For that I considered a situation in which a bet of 2 points is called in a round where we have at least 50% odds of winning, and we lose a point for every round we have less than 50% odds of winning. (Include formulas). Then I stored the expected values of each hand (again one for being Mano and one for not being Mano) in the same .json file. This expected value is obviously an approximation, but we do not want to s

Once we have the expected value, we say mus if it is over certain fixed threshold.

2. To discard, we compute all possible discards (there are 15, note that it is mandatory to throw at least a card) and compute the expected value of that discard. For that, we make a reduction and assume that for every free spot we can obtain either a 12, a 10, a 5 or a 1. This assumption reduces the possible hands to only 35, and with that we only have to visit the expected_value dicctionary a few hundred times.



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

## 6. References
[1]: https://arxiv.org/abs/1811.00164