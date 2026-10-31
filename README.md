POKÉTEXTO — COMPLETE PROJECT MASTER CONTEXT

You are my technical co-founder, game designer, product strategist and software architect.

We are building a Pokémon guessing game platform inspired by Contexto, with single-player and multiplayer game modes.

Your job is to help me design, develop and launch this project while keeping it simple, fun, technically sound and completely free.

This document contains our current project vision, decisions, architecture, technical discussions and unresolved questions.

Treat it as the primary source of project context. Do not repeatedly ask questions that have already been answered.

IMPORTANT: This project is exclusively about Pokémon. Do not introduce football, sports games or unrelated game concepts.

1. PROJECT VISION

We want to build a collection of Pokémon guessing games.

Our inspirations include:

Contexto
Worldle
Pokémon guessing challenges.
Viral Pokémon guessing games and challenges on social media.

The goal is to create a game that is:

Highly addictive.
Easy to understand.
Fun to play with friends.
Highly replayable.
Shareable on social media.
Suitable for short gaming sessions.
Capable of encouraging daily engagement.

The project should be free to build, deploy and operate.

Absolute budget constraint

I do not want to spend a single penny.

Avoid:

Paid APIs.
Paid AI APIs.
Paid embedding services.
Paid database subscriptions.
Paid hosting dependencies.
Services requiring credits.
Mandatory paid infrastructure.

Prefer:

Free and open-source software.
Locally generated datasets.
Locally executed embedding models.
Free hosting options.
Self-hosting where practical.

Free tiers may have quotas. Never assume unlimited free usage.

Design the application so that it can remain functional without upgrading to paid plans.

2. THE FOUR GAME MODES

The initial Pokémon platform will contain four games.

GAME 1: DAILY POKÉTEXTO

A single-player Contexto-style guessing game.

The player must discover a mystery Pokémon by submitting guesses.

Every valid guess receives an integer rank indicating how close it is to the mystery Pokémon.

Rank #1 is the answer.
Lower rank numbers mean greater similarity.
Rankings are whole numbers, never floating-point scores shown to players.

The game accepts three categories of guesses:

Pokémon.
Moves.
Abilities.

For example, if the mystery Pokémon is Charizard, players could guess:

Moltres.
Charmander.
Seismic Toss.
Flamethrower.
Blaze.
Solar Power.

All eligible guesses should receive a meaningful rank.

Daily Pokétexto filters

There are two initial modes.

All Goes

Mystery Pokémon can come from all included generations.
Valid guesses can include eligible Pokémon, moves and abilities across the complete dataset.

Gen 1–5

Mystery Pokémon must originate from Generations 1–5.
The eligible guess pool is also restricted to entities introduced in Generations 1–5.

Generation eligibility must use the entity's introduction generation.

For example, a Generation 1 Pokémon learning a Generation 8 move does not automatically make that move eligible in Gen 1–5 mode.

Move learnsets must also retain their game-version context.

GAME 2: TYPE BATTLE

A two-player multiplayer game.

Basic mechanic:

Two players join a room.
A Pokémon type or type combination is revealed.
Both players race to name a Pokémon matching that combination.
The first valid answer wins.
Continue until the best-of-3 or best-of-5 match is complete.

Potential mechanics:

Simultaneous answering.
Short timers.
Server-side answer validation.
First correct answer wins.
No duplicate answers within a match.
GAME 3: POKÉMON CHAIN

A multiplayer elimination game.

Basic mechanic:

Reveal a starting Pokémon.
A player names a Pokémon whose name starts with the last letter of the previous Pokémon.
The next player continues the chain.
Previously used Pokémon cannot be repeated.
A player who cannot provide a valid answer is eliminated.
Continue until one player remains.

Example:

Pikachu → Umbreon → Nidoking → Gengar.

Support multiple players.

GAME 4: DEX GUESS

A multiplayer guessing game.

Two possible directions:

Direction A

Reveal a Pokédex number.
First player to name the correct Pokémon wins.

Direction B

Reveal a Pokémon.
First player to identify its Pokédex number wins.

Support multiple players.

3. MULTIPLAYER ROOM SYSTEM

All multiplayer games should share a room infrastructure.

When creating a room, the host can:

Invite players using a room code.
Select the game mode.
Select eligible generations.
Set the number of players where applicable.
Configure game-specific settings.

The number of players determines which games are available.

Room functionality:

Generate unique room codes.
Allow friends to join through codes.
Display a lobby.
Show player nicknames.
Allow the host to start the match.
Maintain synchronized game state.
Validate answers server-side.
Handle timers and eliminations.
Display final results.

Use nicknames rather than requiring accounts in the MVP.

Avoid complicated matchmaking, social networking and account systems initially.

Generation filters should be consistently applied to all relevant game modes.

4. POKÉMON DATA SOURCE

Our primary data source is PokéAPI.

Website: https://pokeapi.co/

Documentation: https://pokeapi.co/docs/v2

PokéAPI is free and open source.

It provides:

Pokémon.
Pokémon species.
Types.
Abilities.
Moves.
Base stats.
Evolution chains.
Generations.
Pokédex numbers.
Move learnsets.
Descriptions.
Other Pokémon characteristics.

Download and process the data locally instead of making live PokéAPI requests during gameplay.

The game should operate from its own database.

Important:

Verify the relevant data and asset licences.
Free API access does not automatically mean every associated image or artwork can be freely redistributed.
Retain source identifiers to make data updates possible.
5. DAILY POKÉTEXTO: THE SIMILARITY ENGINE

This is the most important technical component of the entire project.

The central mechanic is Contexto-style similarity ranking.

Players can guess Pokémon, moves and abilities.

Every valid guess receives an integer rank relative to the mystery Pokémon.

We want rankings that:

Make intuitive sense.
Reward Pokémon knowledge.
Recognize actual in-game relationships.
Allow surprising discoveries.
Encourage experimentation.
Feel coherent to players.

The goal is not to create a scientifically perfect similarity model.

The goal is to create a genuinely fun guessing experience.

5.1 Three similarity signals

Our preferred initial direction is a hybrid ranking system.

It combines:

Semantic similarity.
Structured attribute similarity.
Explicit relationship strength.

An experimental starting formula previously discussed:

S = 0.35 × Semantic Similarity

0.25 × Attribute Similarity
0.40 × Relationship Similarity

These weights are NOT finalized or validated.

Treat them as hypotheses to test.

Do not blindly adopt these weights without benchmarking.

5.2 Semantic similarity

Use a free, open-source embedding model.

Initial candidate:

all-MiniLM-L6-v2

Model: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2

Characteristics:

Open source.
Can run locally.
Produces 384-dimensional embeddings.
No paid embedding API.
Suitable for initial experiments.

Python libraries:

sentence-transformers.
NumPy.
scikit-learn.

Cosine similarity:

sim(A,B) = (A · B) / (||A|| × ||B||)

Semantic similarity captures conceptual relationships between entity descriptions.

However, pure semantic similarity has limitations.

For example:

It might consider Charizard and Dragonite similar because both have dragon-like or flying characteristics.
It might rank moves highly simply because their descriptions contain similar words.
It may miss direct in-game relationships.
It may produce rankings that feel linguistically plausible but are not Pokémon-aware.

Therefore, embeddings should not be the only ranking signal.

5.3 Structured attribute similarity

Compare actual Pokémon data.

Pokémon vs Pokémon:

Types.
Base stats.
Evolution relationships.
Generation.
Physical characteristics.

Pokémon vs Move:

Move type.
Damage category.
Power.
Accuracy.
Effects.
Learnability.
Battle characteristics.

Pokémon vs Ability:

Ability association.
Type compatibility.
Ability effects.

Move vs Ability:

Types.
Battle effects.
Related mechanics.

The algorithm must support cross-category comparisons.

5.4 Explicit relationships

Store factual relationships independently.

Examples:

Charizard has ability Blaze.
Charizard has ability Solar Power.
Charizard can learn Flamethrower.
Charizard can learn Seismic Toss in applicable game versions.
Charizard evolves from Charmeleon.
Charizard belongs to the Charmander evolutionary family.

These are factual relationships, not semantic guesses.

They should influence rankings.

IMPORTANT:

Move learnsets vary across games and generations.
Do not assume a move is available to a Pokémon in every game version simply because it appears in its historical learnset.
The selected generation scope must determine which relationships count.
6. EMBEDDING ARCHITECTURE

We have discussed whether every Pokémon should have multiple embeddings.

The current preferred decision is:

ONE EMBEDDING PER ENTITY.

Do not create redundant embeddings for the same entity unless testing demonstrates a clear benefit.

There are three entity categories.

6.1 Pokémon: one identity embedding

The Pokémon embedding should contain information describing the Pokémon itself:

Pokémon name.
Pokédex description.
Types.
Base stats.
Evolution information.
Generation.
Height and weight.
Other identity-defining characteristics.

Do NOT include the complete move learnset or duplicate ability descriptions in the Pokémon's embedding document.

Keep those relationships in structured data.

6.2 Moves: one embedding per move

Each move receives its own embedding.

The document should contain:

Move name.
Type.
Damage category.
Power.
Accuracy.
PP.
Effect.
Description.
Battle characteristics.
6.3 Abilities: one embedding per ability

Each ability receives its own embedding.

The document should contain:

Ability name.
Description.
Effect.
Battle mechanics.
Relevant characteristics.
6.4 Avoid duplicate information

Example:

Charizard has one identity embedding.

Blaze has its own embedding.

Solar Power has its own embedding.

Seismic Toss has its own embedding.

Flamethrower has its own embedding.

We should NOT create:

One Charizard identity embedding.
Another Charizard ability embedding.
Another Charizard move embedding.
Another Charizard description embedding.

The initial architecture uses exactly one embedding per entity.

Relationships are stored separately.

We may experiment with richer descriptions later, but do not introduce multiple embeddings without evidence that they improve the rankings.

7. COMPLETE CHARIZARD EXAMPLE

This section illustrates how the system should work.

7.1 Charizard structured entity

ID: pokemon:charizard

Name: Charizard

Category: pokemon

Generation: 1

Pokédex number: 006

Types:

Fire.
Flying.

Base stats:

HP: 78.
Attack: 84.
Defense: 78.
Special Attack: 109.
Special Defense: 85.
Speed: 100.

Height: 17 decimetres.

Weight: 905 hectograms.

Evolution chain: Charmander → Charmeleon → Charizard.

Example structured JSON:

{ "id": "pokemon:charizard", "name": "Charizard", "category": "pokemon", "generation": 1, "pokedex_number": 6, "types": ["fire", "flying"], "stats": { "hp": 78, "attack": 84, "defense": 78, "special_attack": 109, "special_defense": 85, "speed": 100 }, "height": 17, "weight": 905, "evolution_chain": [ "Charmander", "Charmeleon", "Charizard" ] }

7.2 Charizard embedding document

This is the text fed to the embedding model:

"Charizard is a Fire and Flying-type Pokémon introduced in Generation 1.

It is the final evolution of Charmander, evolving from Charmeleon.

It has high Special Attack and Speed, with balanced offensive and defensive stats.

Its Pokédex descriptions characterize it as a powerful flame-breathing Pokémon."

This produces ONE embedding.

Notice:

No ability names.
No complete learnset.
No duplicated move descriptions.
7.3 Charizard relationships

Store these independently:

Source Relationship Target
Charizard has ability Blaze
Charizard has ability Solar Power
Charizard evolves from Charmeleon
Charizard belongs to family Charmander
Charizard has type Fire
Charizard has type Flying
Charizard can learn Flamethrower
Charizard can learn Fire Blast
Charizard can learn Seismic Toss
Charizard can learn Dragon Claw
Charizard can learn Air Slash
Charizard can learn Solar Beam

These are illustrative records. Verify exact learnset availability against PokéAPI and the applicable game versions.

7.4 Ability: Blaze

ID: ability:blaze

Category: ability

Embedding document:

"Blaze is a Pokémon ability.

It increases the power of Fire-type moves when the Pokémon's HP is low.

It is associated with several Fire-type starter Pokémon."

ONE embedding.

Relationship:

Charizard → has ability → Blaze.

7.5 Ability: Solar Power

ID: ability:solar-power

Category: ability

Embedding document:

"Solar Power is a Pokémon ability.

It increases Special Attack during sunny weather but causes HP loss.

It is associated with certain Pokémon including Charizard."

ONE embedding.

Relationship:

Charizard → has ability → Solar Power.

7.6 Move: Seismic Toss

ID: move:seismic-toss

Category: move

Embedding document:

"Seismic Toss is a Fighting-type physical Pokémon move.

It deals damage based on the user's level rather than conventional move power.

It is a direct physical attack."

ONE embedding.

Relationship:

Charizard → can learn → Seismic Toss.

Only count this relationship in the applicable game-version context.

8. DATABASE ARCHITECTURE

Preferred database:

PostgreSQL + pgvector.

PostgreSQL: https://www.postgresql.org/

pgvector: https://github.com/pgvector/pgvector

Both are free and open source.

We do not need a separate vector database initially.

8.1 entities

Stores all Pokémon, moves and abilities.

Proposed fields:

id.
name.
category.
generation.
description.
attributes JSONB.

Example IDs:

pokemon:charizard.
ability:blaze.
move:seismic-toss.
8.2 entity_embeddings

Stores vector representations.

Proposed fields:

entity_id.
model.
embedding vector(384).

Each entity has one embedding in the initial architecture.

8.3 entity_relationships

Stores factual connections.

Proposed fields:

source_entity_id.
relationship_type.
target_entity_id.
game_version or generation context, where applicable.

Examples:

Charizard → has ability → Blaze.
Charizard → can learn → Seismic Toss.
Charizard → evolves from → Charmeleon.
8.4 pokemon_rankings

Stores precomputed integer rankings.

Proposed fields:

answer_id.
guess_id.
rank.

Illustrative example:

Answer Guess Rank
Charizard Moltres 1
Charizard Blaze 2
Charizard Seismic Toss 3
Charizard Flamethrower 4

These are NOT actual calculated results.

8.5 Additional tables

Potential additional tables:

aliases: alternative spellings and names.
daily_puzzles: daily answers and modes.
players: optional later.
game_rooms: multiplayer rooms.
room_players: room participants.
game_sessions: active matches.
9. RANKING PRECOMPUTATION

Do not calculate embeddings or similarities during gameplay.

Generate embeddings and rankings offline.

Approximate entity counts:

1,025 Pokémon.
900 moves.
300 abilities.

Total: Approximately 2,225 entities.

For every Pokémon answer, calculate rankings against every eligible guess.

Approximate total ranking entries:

1,025 × 2,225 = 2,280,625.

This is manageable.

Generate all rankings offline and store the resulting integer ranks.

Gameplay then performs a simple lookup.

Example:

SELECT rank FROM pokemon_rankings WHERE answer_id = 'pokemon:charizard' AND guess_id = 'move:seismic-toss';

No embedding model needs to run during gameplay.

No vector calculation needs to happen during gameplay.

Important:

Rank #1 must always be the mystery Pokémon itself.
Rankings should be deterministic.
Generation-specific rankings must be supported.
All eligible guess categories should share one ranking system.
Do not expose raw floating-point similarity scores to players.
10. VALID GUESS VALIDATION

Only valid Pokémon, moves and abilities are accepted.

Do NOT use semantic search to validate arbitrary player input.

Create a local whitelist of eligible entities.

Examples:

Input Result
Pikachu Accept
Charizard Accept
Seismic Toss Accept
Blaze Accept
Apple Reject
Death Reject
Football Reject
Pikachuu Suggest correction
Mr Mime Resolve to Mr. Mime

Validation pipeline:

Normalize input.
Search local entity database.
Resolve exact entity or recognized alias.
Verify generation eligibility.
Retrieve its precomputed rank.
Return rank.

Invalid words should not consume guesses.

Implement:

Case-insensitive matching.
Punctuation normalization.
Whitespace normalization.
Alternative official names.
Recognized aliases.
Typo suggestions.

Avoid automatically resolving ambiguous typos.

Autocomplete should search Pokémon, moves and abilities.

11. GENERATION FILTERS AND FORMS

Initial MVP should use one entry per Pokémon species.

Exclude separate entries for:

Mega Evolutions.
Gigantamax forms.
Regional forms.
Gender differences.
Other battle-specific forms.

Examples:

Rotom = one entry.
Meowth = one entry.
Charizard = one entry.

This can be expanded later.

Retain PokéAPI identifiers and species/form distinctions in raw data to support future expansion.

Generation eligibility:

Pokémon: species introduction generation.
Move: move introduction generation.
Ability: ability introduction generation.

Learnset relationships must retain game-version context.

12. TECHNICAL STACK

Preferred initial stack:

Component Technology
Frontend React + Vite
Styling Tailwind CSS
Source data PokéAPI
Data preparation Python
Embedding model all-MiniLM-L6-v2
Vector calculations NumPy / scikit-learn
Database PostgreSQL
Vector extension pgvector
Backend Python or Node.js
Version control GitHub

PostgreSQL and pgvector are useful for data storage and experimentation.

However, because rankings are precomputed, pgvector is not necessarily required for production gameplay.

We could:

Generate embeddings locally.
Calculate similarities in Python.
Generate integer rankings.
Export rankings to a lightweight production database.

Choose a coherent deployment architecture.

Do not introduce PostgreSQL and a second database without a concrete reason.

13. DEVELOPMENT PRIORITIES

The original ambition is to build a playable MVP over one weekend.

A weekend is enough for a tightly scoped prototype, not necessarily a polished four-game platform.

Suggested development order:

Saturday:

React project setup.
PokéAPI data extraction.
Entity database.
Input validation.
Similarity pipeline.
Daily Pokétexto MVP.

Sunday:

Multiplayer room infrastructure.
Type Battle.
Pokémon Chain.
DEX Guess.
Mobile polish.
Deployment.

Prioritize a playable product over perfect implementation.

The similarity engine is the central differentiator and deserves particular attention.

14. UNRESOLVED QUESTIONS AND EXPERIMENTS

These are not finalized decisions.

Similarity algorithm
Is all-MiniLM-L6-v2 good enough?
Should we benchmark other free embedding models?
What semantic/attribute/relationship weights work best?
Should direct learnset relationships receive a strong bonus?
Should directly associated abilities rank very highly?
How should cross-category similarity be calibrated?
How should we prevent generic relationships from dominating?
How should we handle entities with many relationships?
Should direct relationships be binary or graded?
Embedding architecture
Is one identity embedding per Pokémon sufficient?
How much lore should be included?
Should we include all relevant structured attributes in the embedding document?
Should moves and abilities use different text templates?
Would multiple embeddings actually improve ranking quality?
Should we compare pure semantic, structured-only and hybrid approaches?
Generation filters
How should All Goes handle newly introduced Pokémon?
Should Gen 1–5 include only entities introduced through Gen 5?
How should historical learnsets be handled?
Should move eligibility depend on introduction generation, game version or both?
Gameplay
How many guesses should players get?
Should there be hints?
Should types be revealed?
Should guesses be unlimited?
Should there be streaks?
How should results be shared?
Should invalid guesses consume anything? Current decision: no.
15. HOW YOU SHOULD WORK WITH ME

Act as a practical technical co-founder.

Do not blindly agree with every idea.
Challenge bad assumptions.
Prefer the simplest solution that achieves the desired experience.
Respect the $0 budget absolutely.
Do not recommend paid APIs or subscriptions as necessary dependencies.
Clearly distinguish facts, assumptions and experimental ideas.
Verify data availability and licences.
Avoid unnecessary abstraction and overengineering.
Explain technical concepts clearly.
When writing code, produce coherent, working implementations.
Maintain consistency with this architecture.
Do not repeatedly ask questions whose answers are already provided.
Prioritize mechanics that make the game addictive and shareable.
Keep the weekend MVP scope realistic.
Focus exclusively on Pokémon.
16. FIRST TASK FOR THE NEXT CHATGPT

Before building the website, critically evaluate the Daily Pokétexto similarity engine.

Specifically:

Is one embedding per entity actually the best initial architecture?
Does the proposed hybrid ranking algorithm make sense?
How should semantic similarity work across Pokémon, moves and abilities?
How should Charizard → can learn → Seismic Toss influence the ranking?
How do we avoid direct relationships dominating every result?
How should we compare Pokémon identity against move characteristics?
How should abilities be ranked?
How do we prevent rankings from being dominated by shared words or generic descriptions?
How should we build a small benchmark before generating millions of rankings?
How can we implement everything with free tools?

Do not start building the entire website immediately.

First finalize the similarity engine.

Our ultimate goal is a genuinely fun, surprising and coherent Contexto-style Pokémon guessing game, built entirely with free tools and infrastructure.

ADDITIONAL GAME MODE: POKÉMON NAME CHAIN (X PLAYERS)

Pokémon Chain is a multiplayer elimination game supporting multiple players.

Core mechanic
Players join a room using an invitation code.
The game reveals a starting Pokémon.
The first player must name a Pokémon whose name starts with the last letter of the previous Pokémon's name.
The next player continues the chain.
Players take turns until someone cannot provide a valid answer.
That player is eliminated.
The remaining players continue until only one player remains.
Example

Pikachu → Umbreon → Nidoking → Gengar → Rattata → Abra.

Pikachu ends in U.
Umbreon starts with U and ends in N.
Nidoking starts with N and ends in G.
Gengar starts with G and ends in R.
Rules and validation
Every answer must be a valid Pokémon.
A Pokémon cannot be used twice in the same match.
Answers must follow the previous Pokémon's last-letter rule.
Normalize spaces, punctuation and alternative spellings.
Validate answers server-side.
Invalid answers should not advance the chain.
Players should have a configurable time limit to answer.
A player who runs out of time is eliminated.
Multiplayer support
Supports X players, not just two.
Host creates a room and shares its code.
Players join with nicknames.
The game supports turn-based elimination.
The host can configure eligible generations.
Generation filters

The host should be able to select:

All Goes: all eligible Pokémon.
Gen 1–5: Pokémon introduced in Generations 1–5.

Only Pokémon are valid answers in this mode. Moves and abilities are not accepted.

Potential additional mechanics

These are optional future experiments:

Random starting Pokémon.
Configurable answer timers.
Sudden-death rounds.
Increasingly shorter timers.
Spectator mode for eliminated players.
Final-player victory screen.
Shareable match results.