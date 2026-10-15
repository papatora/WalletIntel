> For the complete documentation index, see [llms.txt](https://docs.trench.bot/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://docs.trench.bot/bundle-tools/bundle-scanner-guide.md).

# Bundle Scanner Guide

General info about bundles and our scanner

This is a slightly longer and educative page about bundling on pump fun, for general FAQ about @TrenchScannerBot please go to [#faq](#faq "mention")

## :exclamation:What is a "bundle"?

*P.S: This is a long section going into technical (but important) definitions and implications*

If you're new here, bundling is an action that token developers use to control large amounts of their supply. This is common nowadays to ensure that bad actors (rogue whales or snipers) don't ruin the momentum of a token significantly. The problem with bundles stems from the team/dev being THE bad actor.   \
\
&#x20;There have been a few forms of it over the past year or so on SOL, and @TrenchScannerBot is designed only to catch the latest and most frequently used method.&#x20;

### Bundling Origins

Before pump.fun, the term bundling meant "putting multiple transaction instructions in one transaction". In simple terms, devs could use multiple wallets to buy the same coin in the same exact transaction. This was commonly done in the same transaction where the LP was deployed. It was understandable as teams didn't want snipers to catch any destructive amount of the supply on launch, so they caught that supply themselves. Essentially, tokens would be deployed AND bought up in the same transaction.\
\
With time, users figured out these bundles can easily be detected by just looking at the first few transactions.&#x20;

### :pill: Pump.fun Bundling History

When pump.fun first launched, devs used the same tactic as bundling originally. When creating a token you're prompted with how much SOL you want to buy. This in of itself is a "bundle" that's built in with pump.fun. Your buy transaction (as a dev) is bundled with the token creation and launch. This was also easily detectable and easy to check with the UI directly.&#x20;

To gain more leverage, teams started adding more and more wallets into that initial creation transaction. That's where it initially started. This ensured that no snipers bought and gave the teams a large amount of supply.  \
\
However, with time trading terminals and bots adapted to this and easily showed these sorts of bundles extremely easily. It also became even harder to do it after pump.fun implemented built in bubblemap support.

### :thinking: So, what changed?

The newest way to bypass these checks was to do an orchestrated *mass snipe* rather than a traditional bundle. We will use the term bundle from here on out to keep it simple. \
\
The way it works is that a slot (or a block) gets queued for multiple buys at once. All the buys are then executed in *separate transactions* but within the same 0.4 seconds or so. Pump.fun has built in warnings for this, but they're not very detailed and it's hard to group when there's a lot of other transactions. Here's what it looks like:

<figure><img src="https://2821085361-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2Fhfezr3vquyRvyuNwhInx%2Fuploads%2F3IiUDjTfiPi7TSw8NWbc%2Fimage.png?alt=media&amp;token=3d80f493-38a4-4b80-8613-cdfa13eb53ef" alt=""><figcaption><p>The warning signs are the <span data-gb-custom-inline data-tag="emoji" data-code="26a0">⚠️</span> on the right</p></figcaption></figure>

This means all 3 buy transactions were in the same exact slot with only a few milliseconds apart. These buys are usually orchestrated by the team and the chances of this occurring are *very low* **BUT** possible (more on that later).

With pump.fun's UI and a bunch of other transactions flowing in, this can be a bit hard to distinguish from a quick look, this is where Trench Radar comes in.

### :rotating\_light: TrenchRadar's Part

Very simply put, we just grab all the transactions with a :warning: next to them and re-display them in a nice and comprehensive format. We also quickly scan the holders of a the token to check if the wallets involved in a bundle are still holding or not, and how much they're holding.<br>

<figure><img src="https://2821085361-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2Fhfezr3vquyRvyuNwhInx%2Fuploads%2FwB1BiO6c5zf8vHVqmE4Q%2Fimage.png?alt=media&amp;token=ba3c5163-ed9c-41f4-913a-608fa8846682" alt=""><figcaption><p>TrenchRadar Sample<br></p></figcaption></figure>

We tell you each slot, how many unique wallets bought in that slot, how much SOL they've spent, and how much they're still holding. This data is once again derived from the pump.fun transactions directly and we don't bring anything from our side. We just make it easier to check because otherwise it would require a LOT of digging. That's not ideal for the quick-pace of these tokens.

### :warning: Considerations

Our bundle checker is by no means perfect. It's a simple transaction slot viewer, and you have to understand that two *UNRELATED* wallets could sometimes purchase in the same slot. This would happen if someone has two wallets loaded on something like BullX (they have multi-wallet buys), or someone with a very fast copytrading bot. If a token also has a lot of eyes on it and a lot of people are trying to buy it, two transactions can be processed in the same slot \
\
Generally speaking, don't pay too much attention to bundles that have 2 wallets with a low %. You should mostly be looking for 3+ wallets that are holding larger amounts of supply. Those will never happen by chance.\
\
An easy red flag is if a token scan looks like this:

&#x20;![](https://2821085361-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2Fhfezr3vquyRvyuNwhInx%2Fuploads%2FBlQbuNuGee80ez7TxHvi%2Fimage.png?alt=media\&token=7a039e01-6330-4f65-9ca1-34422150cfd4)

You can see 24 wallets bought within the same 0.4 seconds, and are holding 76% of the supply. That is an extremely deliberate bundle and will most likely go to 0 within a few minutes. \
\
Some "bad" bundles could have multiple 5-wallet bundles, or some 10-15 wallet bundles, etc. If you see a bunch of random 2 wallet ones that are far apart, this is likely a false positive. <br>

## :question: FAQ

Here are some frequently asked questions:

#### 1. I keep getting "Server Error" when scanning, why is that?

Make sure you're scanning a pump fun token. We only provide our service for pump.fun launches and we don't have any data available for other launches (moonshot or a normal raydium launch)

#### 2. Why do you only support pump.fun right now? And do you plan on adding other ones?

For now there's not a huge demand on adding other launchpads. Pump.fun is holding the most volume, and the type of bundling we scan is the most prominent on pump.fun only. You wouldn't find it anywhere else

#### 3.  Your scanner is showing bundled % over 100% of supply. Is it broken?!

Yes, we know. This is normal. There are two distinct categories, **"Total bundled %"**, and **"Current held %".** \
\
Take this scenario: a dev bundles 10% of the supply, sells it all in one clip to shake people out or stage a CTO, THEN buys up again that 10%.  That will display as 20% in **Total Bundle**, but in reality it's only 10% still. \
\
Good practice is to **ALWAYS** check Current Held Percentage. If that's low or close to 0, it's safe.&#x20;

#### 4. I'm a dev, and I didn't bundle my coin. Why is it showing up on scans?!

Unfortunately, false positives happen, and as you've read above the bot mechanisms are extremely simple and we don't come up with anything not on pump.fun. Most likely what happened is one of these:\
&#x20;  • Someone has a sniper set up and sniped some of your supply.\
&#x20;  • Someone has a heavily copytraded wallet, and two transactions landed in the same block\
&#x20;  • Someone else is controlling your supply\
&#x20;\
Thankfully though, the above cases usually never hold anything serious, at most its 1-2% per bundle.&#x20;

#### 5. Why aren't bundled team wallets showing up on bubblemaps?&#x20;

Ever since pump.fun implemented built-in bubblemaps, devs immediately evolved to bypass it. Some beginners may be caught on bubblemaps, but most the launches you see will have a clean bubblemap.\
\
:question: **So, how does it work?**\
Simply put, devs would normally fund a main wallet with a CEX or a mixer, and THEN fund all related wallets in a bundle. This also includes the dev wallet. What happens is that bubblemaps will not connect the wallets as long as the funder wallet is not involved in the coin. Digging that far back is a bit more technical and intensive to do for thousands of coins, so that's likely why that layer is omitted.\
\
This means devs can easily fund wallets and bundle their supply without showing on bubblemaps, which is how so many people lose because a coin "looks clean"\
\
If you want to avoid it without using TrenchRadar, or you want to make sure they're team wallets, you can check the dev wallet on Solscan, and see if it was funded buy a funder wallet like that. Sometimes the bundle funding is made with a CEX and the dev wallet is also made with a CEX transfer. <br>

***

That's it! If you have any more questions, you can always contact @maroon280 on telegram! I respond most the time but if I don't you can re-send your question!\
\
Our bundle scanner is free to use for all, and will not have a paid/faster version. There are no associated tokens with trench radar either, and all launches are scams.&#x20;
