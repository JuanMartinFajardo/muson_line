// ==========================================
// ESTILOS DINÁMICOS PARA AMPLIAR CARTAS (UX)
// ==========================================
const tutStyles = document.createElement('style');
tutStyles.innerHTML = `
    .tut-cards-group {
        display: flex;
        justify-content: center;
        transition: transform 0.22s ease-in-out;
        transform-origin: center;
        cursor: pointer;
        touch-action: manipulation;
        position: relative;
        z-index: 10;
    }
    
    /* Regla limpia para solapar las cartas de los ejemplos */
    .tut-overlap img + img {
        margin-left: -18px;
    }
    
    /* Súper Zoom en Ordenador (PC) - Incrementado a 1.75x */
    @media (min-width: 769px) {
        .tut-cards-group:hover {
            transform: scale(1.75);
            z-index: 999;
        }
        .tut-cards-group:hover img {
            box-shadow: 0 10px 25px rgba(0,0,0,0.65);
        }
    }
    
    /* Súper Zoom en Móvil - Incrementado a 1.9x */
    .tut-cards-group.tut-mobile-zoom {
        transform: scale(1.9);
        z-index: 999;
    }
    .tut-cards-group.tut-mobile-zoom img {
        box-shadow: 0 12px 28px rgba(0,0,0,0.75);
    }
    
    .tut-zoom-hint {
        font-size: 0.72em;
        color: #88c0d0;
        opacity: 0.65;
        margin-top: 6px;
        margin-bottom: 12px;
        font-style: italic;
        letter-spacing: 0.5px;
        display: block;
        text-align: center;
    }
`;
document.head.appendChild(tutStyles);



// ==========================================
// MOTOR DEL TUTORIAL DE MUS (INGLÉS)
// ==========================================

const tutorialSlides = [
    {
        title: "The Spanish Deck",
        content: `
            <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 20px;">Mus is played with a traditional 40-card Spanish deck, divided into 4 suits.</p>
            
            <div style="display: flex; justify-content: center; gap: 15px; margin-bottom: 25px;">
                <div style="background: #3b4252; padding: 10px; border-radius: 8px; width: 60px;">🪙<br><span style="font-size: 0.8em; color: #88c0d0;">Coins</span></div>
                <div style="background: #3b4252; padding: 10px; border-radius: 8px; width: 60px;">🍷<br><span style="font-size: 0.8em; color: #88c0d0;">Cups</span></div>
                <div style="background: #3b4252; padding: 10px; border-radius: 8px; width: 60px;">⚔️<br><span style="font-size: 0.8em; color: #88c0d0;">Swords</span></div>
                <div style="background: #3b4252; padding: 10px; border-radius: 8px; width: 60px;">🏏<br><span style="font-size: 0.8em; color: #88c0d0;">Clubs</span></div>
            </div>

            <p style="font-size: 1em; color: #d8dee9; margin-bottom: 15px;">Each suit contains numbers from <b>1 to 7</b>, and three special "Figures":</p>
            
            <div class="tut-cards-group" style="gap: 12px; align-items: center; margin: 0 auto; max-width: max-content; padding: 5px;">
                <div style="display: flex; flex-direction: column; align-items: center;">
                    <img src="/static/img/card_coins_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px; box-shadow: 0 4px 8px rgba(0,0,0,0.5);">
                    <span style="color: #ebcb8b; font-weight: bold; margin-top: 5px; font-size: 0.85em;">Jack (10)</span>
                </div>
                <div style="display: flex; flex-direction: column; align-items: center;">
                    <img src="/static/img/card_coins_11.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px; box-shadow: 0 4px 8px rgba(0,0,0,0.5);">
                    <span style="color: #ebcb8b; font-weight: bold; margin-top: 5px; font-size: 0.85em;">Knight (11)</span>
                </div>
                <div style="display: flex; flex-direction: column; align-items: center;">
                    <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px; box-shadow: 0 4px 8px rgba(0,0,0,0.5);">
                    <span style="color: #ebcb8b; font-weight: bold; margin-top: 5px; font-size: 0.85em;">King (12)</span>
                </div>
            </div>
            <span class="tut-zoom-hint">🔍 Hover or tap figures to zoom</span>
        `
    },
    {
        title: "The Royal Secret: 3s & 2s",
        content: `
            <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 20px;">In Mus, there are no actual 3s or 2s. They are impostors! We play with 8 Kings and 8 Aces.</p>
            
            <div style="background: rgba(46, 52, 64, 0.6); border: 1px solid #4c566a; border-radius: 8px; padding: 15px; margin-bottom: 20px;">
                <p style="margin-top: 0; color: #ebcb8b; font-weight: bold;">Every 3 is a King</p>
                <div style="display: flex; justify-content: center; align-items: center; gap: 15px;">
                    <img src="/static/img/card_cups_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px;">
                    <span style="font-size: 2em; color: #a3be8c;">&rarr;</span>
                    <img src="/static/img/card_cups_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px; box-shadow: 0 0 15px rgba(235, 203, 139, 0.5);">
                </div>
            </div>

            <div style="background: rgba(46, 52, 64, 0.6); border: 1px solid #4c566a; border-radius: 8px; padding: 15px;">
                <p style="margin-top: 0; color: #88c0d0; font-weight: bold;">Every 2 is an Ace (1)</p>
                <div style="display: flex; justify-content: center; align-items: center; gap: 15px;">
                    <img src="/static/img/card_coins_02.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px;">
                    <span style="font-size: 2em; color: #a3be8c;">&rarr;</span>
                    <img src="/static/img/card_coins_01.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 60px; border-radius: 4px; box-shadow: 0 0 15px rgba(136, 192, 208, 0.5);">
                </div>
            </div>
        `
    },
   {
        title: "The Mus Phase (Discards)",
        content: `
            <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 20px;">After dealing 4 cards, players decide if they want to discard to improve their hands. This is called asking for <b>"Mus"</b>.</p>
            
            <div style="display: flex; flex-direction: column; align-items: center; gap: 10px; margin-bottom: 20px; font-size: 0.9em;">
                
                <div style="background: #4c566a; color: white; padding: 10px 20px; border-radius: 20px; font-weight: bold;">
                    1. Deal 4 cards
                </div>
                
                <div style="color: #88c0d0;">&darr;</div>
                
                <div style="background: #3b4252; border: 2px solid #88c0d0; color: #eceff4; padding: 15px; border-radius: 8px; text-align: center; width: 80%;">
                    <b>Do BOTH players want Mus?</b>
                </div>
                
                <div style="display: flex; justify-content: space-between; width: 90%; margin-top: 5px;">
                    <div style="display: flex; flex-direction: column; align-items: center; width: 45%;">
                        <div style="color: #a3be8c; font-weight: bold; margin-bottom: 5px;">YES</div>
                        <div style="color: #a3be8c;">&darr;</div>
                        <div style="background: rgba(163, 190, 140, 0.2); border: 1px solid #a3be8c; color: #a3be8c; padding: 10px; border-radius: 8px; text-align: center; font-size: 0.9em;">
                            Discard 1-4 cards.<br>Draw new ones.<br><i>(Loop back)</i>
                        </div>
                    </div>
                    
                    <div style="display: flex; flex-direction: column; align-items: center; width: 45%;">
                        <div style="color: #bf616a; font-weight: bold; margin-bottom: 5px;">NO (Cut)</div>
                        <div style="color: #bf616a;">&darr;</div>
                        <div style="background: rgba(191, 97, 106, 0.2); border: 1px solid #bf616a; color: #bf616a; padding: 10px; border-radius: 8px; text-align: center; font-size: 0.9em;">
                            The dealing stops.<br>Betting starts immediately.
                        </div>
                    </div>
                </div>
            </div>
            
            <p style="font-size: 0.9em; color: #d8dee9; font-style: italic;">* If you have a good hand, cut the Mus to prevent the opponent from improving theirs!</p>
        `
    },
    {
        title: "The 4 Betting Phases",
        content: `
            <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 15px;">Once the Mus is cut, players bet sequentially in 4 distinct phases:</p>
            
            <div style="display: flex; flex-direction: column; gap: 10px; text-align: left;">
                
                <div style="background: #3b4252; border-left: 5px solid #ebcb8b; padding: 10px 15px; border-radius: 4px;">
                    <strong style="color: #ebcb8b; font-size: 1.1em;">⬆️ Grande (High)</strong>
                    <p style="margin: 5px 0 0 0; font-size: 0.95em; color: #d8dee9;">The highest cards win. (Kings > Knights > Jacks...)</p>
                </div>

                <div style="background: #3b4252; border-left: 5px solid #88c0d0; padding: 10px 15px; border-radius: 4px;">
                    <strong style="color: #88c0d0; font-size: 1.1em;">⬇️ Chica (Low)</strong>
                    <p style="margin: 5px 0 0 0; font-size: 0.95em; color: #d8dee9;">The lowest cards win. (Aces > 4s > 5s...)</p>
                </div>

                <div style="background: #3b4252; border-left: 5px solid #b48ead; padding: 10px 15px; border-radius: 4px;">
                    <strong style="color: #b48ead; font-size: 1.1em;">👯 Pares (Pairs)</strong>
                    <p style="margin: 5px 0 0 0; font-size: 0.95em; color: #d8dee9;">You can only bet if you have 2 or more matching cards. (2 pairs > 3 of a kind > 1 pair).</p>
                </div>

                <div style="background: #3b4252; border-left: 5px solid #a3be8c; padding: 10px 15px; border-radius: 4px;">
                    <strong style="color: #a3be8c; font-size: 1.1em;">🎯 Juego (Game)</strong>
                    <p style="margin: 5px 0 0 0; font-size: 0.95em; color: #d8dee9;">Sum the value of your cards (Figures = 10). You need <b>31 or more</b>. The best is 31, followed by 32, then 40, then 37, 36, 35, 34, and finally 33. <br><i>*If nobody reaches 31, we play for the closest "Punto" (Point).</i></p>
                </div>

            </div>
        `
    },
    {
        title: "The Betting Language",
        content: `
            <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 20px;">During a phase, you can start a bet or respond to one. Here is your arsenal:</p>
            
            <div style="display: flex; flex-direction: column; gap: 8px; text-align: left;">
                
                <div style="display: flex; gap: 10px;">
                    <div style="background: #a3be8c; color: #2e3440; padding: 10px; border-radius: 4px; font-weight: bold; width: 80px; text-align: center;">Bid</div>
                    <div style="background: #3b4252; color: #d8dee9; padding: 10px; border-radius: 4px; flex-grow: 1;">You bet 2 points.</div>
                </div>

                <div style="display: flex; gap: 10px;">
                    <div style="background: #4c566a; color: white; padding: 10px; border-radius: 4px; font-weight: bold; width: 80px; text-align: center;">Pass</div>
                    <div style="background: #3b4252; color: #d8dee9; padding: 10px; border-radius: 4px; flex-grow: 1;">You don't bet. If both pass, the phase is left at 0 points.</div>
                </div>

                <div style="width: 100%; height: 1px; background: #4c566a; margin: 5px 0;"></div>

                <div style="display: flex; gap: 10px;">
                    <div style="background: #88c0d0; color: #2e3440; padding: 10px; border-radius: 4px; font-weight: bold; width: 80px; text-align: center;">Call</div>
                    <div style="background: #3b4252; color: #d8dee9; padding: 10px; border-radius: 4px; flex-grow: 1;">You <b>Call</b> the bet. The points are locked until the end.</div>
                </div>

                <div style="display: flex; gap: 10px;">
                    <div style="background: #bf616a; color: white; padding: 10px; border-radius: 4px; font-weight: bold; width: 80px; text-align: center;">Fold</div>
                    <div style="background: #3b4252; color: #d8dee9; padding: 10px; border-radius: 4px; flex-grow: 1;">You <b>Fold</b>. The opponent instantly wins 1 point (or the previous bet).</div>
                </div>

                <div style="display: flex; gap: 10px;">
                    <div style="background: #ebcb8b; color: #2e3440; padding: 10px; border-radius: 4px; font-weight: bold; width: 80px; text-align: center;">Órdago</div>
                    <div style="background: #3b4252; color: #d8dee9; padding: 10px; border-radius: 4px; flex-grow: 1;"><b>ALL-IN!</b> If accepted, the game ends immediately!</div>
                </div>

            </div>
        `
    },
    {
        title: "Mano vs. Postre",
        content: `
            <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 20px;">Position is everything in Mus. The roles swap every round.</p>
            
            <div style="display: flex; justify-content: space-between; gap: 15px; margin-bottom: 20px;">
                
                <div style="background: #3b4252; border: 2px solid #ebcb8b; border-radius: 8px; padding: 15px; width: 48%; position: relative;">
                    <div style="position: absolute; top: -15px; left: 50%; transform: translateX(-50%); font-size: 1.5em;">👑</div>
                    <h3 style="color: #ebcb8b; margin-top: 10px; margin-bottom: 5px;">Mano (Hand)</h3>
                    <p style="font-size: 0.9em; color: #d8dee9; text-align: left; margin: 0;">
                        • Speaks <b>first</b>.<br>
                        • Wins all absolute <b>ties</b>.<br>
                    </p>
                </div>

                <div style="background: #3b4252; border: 2px solid #81a1c1; border-radius: 8px; padding: 15px; width: 48%;">
                    <h3 style="color: #81a1c1; margin-top: 10px; margin-bottom: 5px;">Postre (Last)</h3>
                    <p style="font-size: 0.9em; color: #d8dee9; text-align: left; margin: 0;">
                        • Speaks <b>last</b> (huge information advantage).<br>
                        • Must have strictly better cards to win.
                    </p>
                </div>

            </div>
            
            <div style="background: rgba(235, 203, 139, 0.1); border-left: 4px solid #ebcb8b; padding: 10px; color: #eceff4; font-size: 0.95em; text-align: left;">
                <b>The Golden Rule:</b> If you have exactly the same cards as the opponent, the Mano always wins!
            </div>
        `
    },
    {
        title: "The Counting Phase (Points)",
        content: `
            <p style="font-size: 1em; color: #eceff4; margin-bottom: 15px;">At the end of the round, you reveal your cards. The winner of each phase gets the <b>Bets</b> from the table, plus <b>Bonus Points</b> for the cards you hold:</p>
            
            <div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;">
                
                <div style="background: #3b4252; padding: 10px; border-radius: 6px; width: 45%; text-align: left;">
                    <div style="color: #88c0d0; font-weight: bold; margin-bottom: 5px;">Grande & Chica (High & Low)</div>
                    <div style="font-size: 0.85em; color: #d8dee9;">No bonus points. You only win the bets placed (or 1 pt if both passed).</div>
                </div>

                <div style="background: #3b4252; padding: 10px; border-radius: 6px; width: 45%; text-align: left;">
                    <div style="color: #a3be8c; font-weight: bold; margin-bottom: 5px;">Punto (Point)</div>
                    <div style="font-size: 0.85em; color: #d8dee9;">Winning the Punto gives <span style="color:#a3be8c; font-weight:bold;">+1 pt</span>.</div>
                </div>

                <div style="background: #3b4252; padding: 10px; border-radius: 6px; width: 93%; text-align: left; display: flex; align-items: center; justify-content: space-between;">
                    <div>
                        <div style="color: #b48ead; font-weight: bold; margin-bottom: 5px;">Pares (Pairs)</div>
                        <div style="font-size: 0.85em; color: #d8dee9;">Simple Pair: <span style="color:#a3be8c; font-weight:bold;">+1 pt</span><br>Three of a kind: <span style="color:#a3be8c; font-weight:bold;">+2 pts</span><br>Two Pairs: <span style="color:#a3be8c; font-weight:bold;">+3 pts</span></div>
                    </div>
                </div>

                <div style="background: #3b4252; padding: 10px; border-radius: 6px; width: 93%; text-align: left; display: flex; align-items: center; justify-content: space-between;">
                    <div>
                        <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px;">Juego (Game)</div>
                        <div style="font-size: 0.85em; color: #d8dee9;">Having 31 exactly: <span style="color:#a3be8c; font-weight:bold;">+3 pts</span><br>Having 32 to 40: <span style="color:#a3be8c; font-weight:bold;">+2 pts</span></div>
                    </div>
                </div>

            </div>
        `
    },
    {
        title: "Advanced Secrets",
        content: `
            <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 15px;">Two rare but powerful hands you must know:</p>
            
            <div style="display: flex; flex-direction: column; gap: 15px; text-align: left;">
                <div style="background: #3b4252; border-left: 5px solid #d08770; padding: 10px 15px; border-radius: 4px;">
                    <strong style="color: #d08770; font-size: 1.1em;">🃏 Pedrete (4-5-6-7)</strong>
                    <div class="tut-cards-group" style="display: flex; gap: 5px; margin: 10px 0;">
                        <img src="/static/img/card_swords_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        <img src="/static/img/card_cups_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        <img src="/static/img/card_coins_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        <img src="/static/img/card_clubs_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                    </div>
                    <span class="tut-zoom-hint" style="margin-bottom: 0;">🔍 Hover or tap cards to zoom</span>
                    <p style="margin: 0; font-size: 0.95em; color: #d8dee9;">This is the worst hand, so to compensate for it, instantly gives you <b style="color:#a3be8c;">+1 pt</b> and you draw 4 new cards! But you <b>must claim it</b> during the Mus phase, before your opponent cuts.</p>
                </div>

                <div style="background: #3b4252; border-left: 5px solid #ebcb8b; padding: 10px 15px; border-radius: 4px;">
                    <strong style="color: #ebcb8b; font-size: 1.1em;">👑 La Real (Royal)</strong>
                    <div class="tut-cards-group" style="display: flex; gap: 5px; margin: 10px 0;">
                        <img src="/static/img/card_coins_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        <img src="/static/img/card_swords_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        <img src="/static/img/card_cups_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                        <img src="/static/img/card_coins_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 40px; border-radius: 3px;">
                    </div>
                    <span class="tut-zoom-hint" style="margin-bottom: 0;">🔍 Hover or tap cards to zoom</span>
                    <p style="margin: 0; font-size: 0.95em; color: #d8dee9;">Three 7s and a Jack (10) form the ultimate 31. This hand <b>always wins the Game phase</b>, even if you are the Postre!</p>
                </div>
            </div>
        `
    },
    {
        title: "Ready to Practice?",
        content: `
            <p style="font-size: 1.1em; color: #eceff4; margin-bottom: 25px;">You know the theory. Now let's see how it plays out on the table.</p>
            
            <div style="display: flex; flex-direction: column; gap: 15px; align-items: center; margin-top: 30px;">
                <button onclick="window.goToSlide(9)" style="width: 85%; background: #81a1c1; color: #2e3440; font-weight: bold; padding: 15px; border-radius: 8px; font-size: 1.1em; border: none; cursor: pointer; transition: 0.2s; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">📖 Read Examples (Step by Step)</button>
                
                <button id="btn-start-interactive" style="width: 85%; background: #a3be8c; color: #2e3440; font-weight: bold; padding: 15px; border-radius: 8px; font-size: 1.1em; border: none; cursor: pointer; transition: 0.2s; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">🎮 Start Practising</button>
            </div>
        `
    },
    {
        title: "Ex 1: High & Low (The Fold)",
        content: `
            <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 10px;">Player 1 has great cards for HIGH, but P2 is strong in LOW.</p>
            
            <div style="display: flex; justify-content: space-around; margin-bottom: 12px; align-items: center;">
                <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                    <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">P1 (Mano)</div>
                    <div class="tut-cards-group tut-overlap">
                        <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        <img src="/static/img/card_cups_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        <img src="/static/img/card_swords_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                    </div>
                    <span class="tut-zoom-hint">🔍 Zoom</span>
                </div>
                <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                    <div style="color: #81a1c1; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">P2 (Postre)</div>
                    <div class="tut-cards-group tut-overlap">
                        <img src="/static/img/card_coins_01.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        <img src="/static/img/card_cups_02.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        <img src="/static/img/card_swords_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                    </div>
                    <span class="tut-zoom-hint">🔍 Zoom</span>
                </div>
            </div>
            
            <div style="display: flex; flex-direction: column; gap: 8px; text-align: left; font-size: 0.85em;">
                <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #ebcb8b;">
                    <strong style="color: #ebcb8b; font-size: 1.1em;">⬆️ HIGH (Grande)</strong><br>
                    <span style="color: #ebcb8b;">P1:</span> <b>Bids 2.</b><br>
                    <span style="color: #81a1c1;">P2:</span> Knows 6 and Ace are terrible for High. <b>Folds (No Ver).</b><br>
                    <div style="margin-top: 5px; color: #a3be8c;"><b>Result:</b> P1 instantly wins <b>1 point</b> (the uncalled bet).</div>
                </div>

                <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #88c0d0;">
                    <strong style="color: #88c0d0; font-size: 1.1em;">⬇️ LOW (Chica)</strong><br>
                    <span style="color: #ebcb8b;">P1:</span> Passes.<br>
                    <span style="color: #81a1c1;">P2:</span> <b>Bids 2.</b><br>
                    <span style="color: #ebcb8b;">P1:</span> Bluffs and <b>Calls (Ver)</b>.<br>
                    <div style="margin-top: 5px; color: #a3be8c;"><b>Result:</b> 2 points locked. P2 will win them during the counting phase!</div>
                </div>
            </div>
        `
    },
    {
        title: "Ex 2: Clash of Pairs",
        content: `
            <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 10px;">Having a pair of Kings is good, but 3 of a kind is better.</p>
            
            <div style="display: flex; justify-content: space-around; margin-bottom: 12px; align-items: center;">
                <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                    <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">P1 (Pair)</div>
                    <div class="tut-cards-group tut-overlap">
                        <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        <img src="/static/img/card_cups_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        <img src="/static/img/card_swords_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                    </div>
                    <span class="tut-zoom-hint">🔍 Zoom</span>
                </div>
                <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                    <div style="color: #81a1c1; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">P2 (3 of a kind)</div>
                    <div class="tut-cards-group tut-overlap">
                        <img src="/static/img/card_coins_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        <img src="/static/img/card_cups_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        <img src="/static/img/card_swords_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                    </div>
                    <span class="tut-zoom-hint">🔍 Zoom</span>
                </div>
            </div>
            
            <div style="display: flex; flex-direction: column; gap: 8px; text-align: left; font-size: 0.85em;">
                <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #b48ead;">
                    <strong style="color: #b48ead; font-size: 1.1em;">👯 PAIRS (Pares)</strong><br>
                    <span style="color: #eceff4; font-style: italic;">Both declare they have pairs.</span><br>
                    <span style="color: #ebcb8b;">P1:</span> Trusts the Kings. <b>Bids 2.</b><br>
                    <span style="color: #81a1c1;">P2:</span> Has 3 of a kind! <b>Raises to 4.</b><br>
                    <span style="color: #ebcb8b;">P1:</span> <b>Calls (Ver).</b><br>
                    <div style="margin-top: 8px; padding: 8px; background: rgba(163,190,140,0.1); color: #a3be8c; border-radius: 4px;">
                        <b>Final Count:</b> P2 reveals the three 4s and crushes P1's Kings. <br>P2 takes the <b>4 bet points</b> + <b>2 bonus pts</b> for the 3 of a kind!
                    </div>
                </div>
            </div>
        `
    },
    {
        title: "Ex 3: 31 vs 32",
        content: `
            <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 10px;">In Game (Juego), 31 is the absolute best. 32 is the worst!</p>
            
            <div style="display: flex; justify-content: space-around; margin-bottom: 12px; align-items: center;">
                <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                    <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">P1 (Sum 32)</div>
                    <div class="tut-cards-group tut-overlap">
                        <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        <img src="/static/img/card_cups_10.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        <img src="/static/img/card_swords_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        <img src="/static/img/card_swords_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                    </div>
                    <span class="tut-zoom-hint">🔍 Zoom</span>
                </div>
                <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                    <div style="color: #81a1c1; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">P2 (Sum 31)</div>
                    <div class="tut-cards-group tut-overlap">
                        <img src="/static/img/card_coins_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        <img src="/static/img/card_cups_11.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        <img src="/static/img/card_swords_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        <img src="/static/img/card_swords_04.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                    </div>
                    <span class="tut-zoom-hint">🔍 Zoom</span>
                </div>
            </div>
            
            <div style="display: flex; flex-direction: column; gap: 8px; text-align: left; font-size: 0.85em;">
                <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #a3be8c;">
                    <strong style="color: #a3be8c; font-size: 1.1em;">🎯 GAME (Juego)</strong><br>
                    <span style="color: #eceff4; font-style: italic;">Both reach 31 or more.</span><br>
                    <span style="color: #ebcb8b;">P1:</span> I'm the Mano, 32 might be enough. <b>Bids 2.</b><br>
                    <span style="color: #81a1c1;">P2:</span> I have exactly 31! <b>ÓRDAGO!</b><br>
                    <span style="color: #ebcb8b;">P1:</span> Knows 32 is terrible. <b>Folds (No Ver).</b><br>
                    <div style="margin-top: 8px; padding: 8px; background: rgba(163,190,140,0.1); color: #a3be8c; border-radius: 4px;">
                        <b>Final Count:</b> P2 takes the 2 bet points immediately. At the end, P2 will also get <b>+3 bonus pts</b> for having 31!
                    </div>
                </div>
            </div>
        `
    },
    {
        title: "Ex 4: Playing for the Point",
        content: `
            <p style="font-size: 0.95em; color: #eceff4; margin-bottom: 10px;">If nobody reaches 31, we play "Punto" (highest sum wins).</p>
            
            <div style="display: flex; justify-content: space-around; margin-bottom: 12px; align-items: center;">
                <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                    <div style="color: #ebcb8b; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">P1 (Sum 29)</div>
                    <div class="tut-cards-group tut-overlap">
                        <img src="/static/img/card_coins_12.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        <img src="/static/img/card_cups_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        <img src="/static/img/card_swords_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        <img src="/static/img/card_swords_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                    </div>
                    <span class="tut-zoom-hint">🔍 Zoom</span>
                </div>
                <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
                    <div style="color: #81a1c1; font-weight: bold; margin-bottom: 5px; font-size: 0.9em;">P2 (Sum 28)</div>
                    <div class="tut-cards-group tut-overlap">
                        <img src="/static/img/card_coins_03.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        <img src="/static/img/card_cups_07.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        <img src="/static/img/card_swords_06.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                        <img src="/static/img/card_swords_05.webp" onerror="this.src='/static/img/card_back.webp'" style="width: 44px; border-radius: 3px;">
                    </div>
                    <span class="tut-zoom-hint">🔍 Zoom</span>
                </div>
            </div>
            
            <div style="display: flex; flex-direction: column; gap: 8px; text-align: left; font-size: 0.85em;">
                <div style="background: #3b4252; padding: 10px; border-radius: 6px; border-left: 4px solid #a3be8c;">
                    <strong style="color: #a3be8c; font-size: 1.1em;">🎯 POINT (Punto)</strong><br>
                    <span style="color: #eceff4; font-style: italic;">"Nobody has Game. Playing for Point."</span><br>
                    <span style="color: #ebcb8b;">P1:</span> 29 is very close to 30 (the max point). <b>Bids 2.</b><br>
                    <span style="color: #81a1c1;">P2:</span> I have 28, maybe it's enough? <b>Calls (Ver).</b><br>
                    <div style="margin-top: 8px; padding: 8px; background: rgba(163,190,140,0.1); color: #a3be8c; border-radius: 4px;">
                        <b>Final Count:</b> P1 reveals 29, P2 reveals 28. P1 wins!<br>P1 takes the <b>2 bet points</b> + <b>1 bonus pt</b> for winning the Point.
                    </div>
                </div>
            </div>
        `
    }

];

let currentSlideIndex = 0;

// Variables del DOM
const modalTutorial = document.getElementById('modal-tutorial');
const tutorialContent = document.getElementById('tutorial-content');
const btnPrev = document.getElementById('tut-prev');
const btnNext = document.getElementById('tut-next');
const dotsContainer = document.getElementById('tut-dots');

// Inicializar el carrusel
function renderSlide(index) {
    const slide = tutorialSlides[index];
    
    // Inyectar HTML
    tutorialContent.innerHTML = `
        <h2 style="color: #a3be8c; font-size: 1.8em; margin-bottom: 20px; margin-top: 0;">${slide.title}</h2>
        <div>${slide.content}</div>
    `;

    // Actualizar visibilidad de botones
    btnPrev.style.visibility = index === 0 ? 'hidden' : 'visible';
    
    if (index === tutorialSlides.length - 1) {
        btnNext.innerText = "Finish";
        btnNext.style.backgroundColor = "#ebcb8b";
    } else {
        btnNext.innerHTML = "Next &rarr;";
        btnNext.style.backgroundColor = "#a3be8c";
    }

    // Actualizar puntitos
    dotsContainer.innerHTML = '';
    tutorialSlides.forEach((_, i) => {
        const dot = document.createElement('div');
        dot.style.width = '10px';
        dot.style.height = '10px';
        dot.style.borderRadius = '50%';
        dot.style.backgroundColor = i === index ? '#88c0d0' : '#4c566a';
        dot.style.transition = '0.3s';
        dotsContainer.appendChild(dot);
    });
}

// Eventos de botones
btnNext.addEventListener('click', () => {
    if (currentSlideIndex < tutorialSlides.length - 1) {
        currentSlideIndex++;
        renderSlide(currentSlideIndex);
    } else {
        cerrarTutorial();
    }
});

btnPrev.addEventListener('click', () => {
    if (currentSlideIndex > 0) {
        currentSlideIndex--;
        renderSlide(currentSlideIndex);
    }
});

document.getElementById('btn-cerrar-tutorial').addEventListener('click', cerrarTutorial);

// Abrir desde el menú principal
document.getElementById('btn-tutorial').addEventListener('click', () => {
    document.getElementById('modal-overlay').style.display = 'flex';
    document.getElementById('modal-overlay').classList.remove('hidden');
    
    // Ocultar resto de modales
    document.getElementById('modal-login').classList.add('hidden');
    document.getElementById('modal-signup').classList.add('hidden');
    const ml = document.getElementById('modal-leaderboard'); if(ml) ml.classList.add('hidden');
    const mp = document.getElementById('modal-privacy'); if(mp) mp.classList.add('hidden');

    modalTutorial.classList.remove('hidden');
    
    // Empezar desde el principio siempre
    currentSlideIndex = 0;
    renderSlide(currentSlideIndex);
});

function cerrarTutorial() {
    modalTutorial.classList.add('hidden');
    document.getElementById('modal-overlay').style.display = 'none';
    document.getElementById('modal-overlay').classList.add('hidden');
}

// Exponer la función para que los botones dentro del HTML puedan usarla
window.goToSlide = function(index) {
    if (index >= 0 && index < tutorialSlides.length) {
        currentSlideIndex = index;
        renderSlide(currentSlideIndex);
    }
};

// Capturar el botón de jugar (Preparando el terreno para el siguiente paso)
document.addEventListener('click', function(e) {
    if (e.target && e.target.id === 'btn-start-interactive') {
        // 1. Cerramos la ventana del tutorial
        cerrarTutorial();
        
        // 2. Simulamos un clic transparente en el botón real de jugar contra el bot
        const btnBot = document.getElementById('btn-jugar-bot');
        if (btnBot) {
            btnBot.click();
        }
    }
});




// ==========================================
// GESTOR INTERACTIVO DE ZOOM PARA MÓVILES
// ==========================================
document.getElementById('tutorial-content').addEventListener('click', function(e) {
    // Buscamos si el clic se ha realizado dentro de un grupo de cartas zoomable
    const group = e.target.closest('.tut-cards-group');
    
    if (group) {
        // Solo actuamos si estamos en una pantalla móvil o tablet
        if (window.innerWidth <= 768) {
            const yaAmpliando = group.classList.contains('tut-mobile-zoom');
            
            // Limpiamos cualquier otra carta que estuviera ampliada en la diapositiva
            document.querySelectorAll('.tut-cards-group').forEach(g => g.classList.remove('tut-mobile-zoom'));
            
            // Si no estaba ampliada, la ampliamos ahora
            if (!yaAmpliando) {
                group.classList.add('tut-mobile-zoom');
            }
        }
    } else {
        // Si el usuario toca en cualquier otra parte de la pantalla, replegamos el zoom activo
        document.querySelectorAll('.tut-cards-group').forEach(g => g.classList.remove('tut-mobile-zoom'));
    }
});