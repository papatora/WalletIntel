> For the complete documentation index, see [llms.txt](https://docs.trench.bot/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://docs.trench.bot/curated-radar/scoring-system.md).

# Scoring System

This is arguably the most important and fundamental part of our curated bot, **Scores.**\
\
Our scoring algorithms are very intricate and sensitive, and still largely under work as we modify and tweak them.\
\
But here's a general understanding of it so you can see why each alert was called.

* Whales purchasing a token increases the score. The score for whales depends on how many there are, how much they've bought, and at which market cap. It also adds a bonus for a whale's win rate if it exists. The system prioritizes micro caps and has a lower tendency to call larger caps. It also doesn't call anything above 10 million market cap. Low win rate whales decrease the score.&#x20;
* Whale + another alert exponentially increases the score. So you may see tokens where only 1 whale has bought them, but they were also bought by an insider or had twitter activity.
* Fresh wallets and insiders are calculated the same as whales, where the score depends on how many wallets and how much they've bought.
* Twitter activity gives a boost depending on what level of activity it has on twitter. "Early alerts" give only a few points, but a "Wide spread" alert gives a lot more
* Every time a token is called, the threshold for the next call is increased by 30%, this makes duplicate calls harder unless there's significant activity.

## :grey\_question: Examples

For instance, you could see a token with only 1 larger whale purchase that gets alerted at 100k market cap. This is because the whale likely has good winrate, and the market cap bonus was significant enough to pass the threshold.\
\
You may also see a token called at a mid-range market cap with only 1 whale and 1 fresh wallet. This is because of the exponential boost that two alerts give each other.\
\
As always, you need to make your best judgement with these alerts, and not all alerts are for buying.

## :thought\_balloon: Considerations & Caution :warning:

While we've tried our best to tweak the algorithm, it's still prone to errors and may call things not worthy of being "curated". \
\
We've decided to release our first beta version with these values, but we've been storing all data points in our databases and we plan on doing rigorous AI training on them. The AI will prioritize a balance between returns and safety, and will be the one deciding the scores and the next score threshold rather than our hard-set math values.\
\
We'll also be taking user feedback on the bot to see what hits better and what still needs work or modification. &#x20;
