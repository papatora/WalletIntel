> For the complete documentation index, see [llms.txt](https://docs.trench.bot/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://docs.trench.bot/bundle-tools/clusters-guide.md).

# Clusters Guide

## Bundle Risk Index (BRI) - User Guide

### 🎯 What is the Bundle Risk Index?

The Bundle Risk Index (BRI) is an advanced analysis system that detects coordinated trading activity in cryptocurrency tokens. It identifies groups of wallets ("clusters") that may be working together to manipulate token prices or create artificial trading volume.

<figure><img src="https://2821085361-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2Fhfezr3vquyRvyuNwhInx%2Fuploads%2F0v2ZSgBE7v3ZSMX8u3nh%2Fimage.png?alt=media&amp;token=aef17407-c917-4b5a-8d66-aca10fe37835" alt=""><figcaption></figcaption></figure>

### 📊 BRI vs Regular Bundle Analysis

#### Key Differences from regular bundles

The Bundle Risk Index (BRI) is a **significant** evolution from the regular bundle scanner:

| Feature                     | Old Bundling              | Bundle Risk Index (BRI)                         |
| --------------------------- | ------------------------- | ----------------------------------------------- |
| **Analysis Depth**          | Basic funding connections | Multi-dimensional risk scoring                  |
| **Temporal Analysis**       | Not included              | Weighted window correlation                     |
| **Risk Scoring**            | Simple grouping           | 0-100% weighted risk scores                     |
| **Confidence Levels**       | Not provided              | 5-tier confidence system                        |
| **Stealth Detection**       | Limited                   | Advanced mixer/obfuscation detection            |
| **Cluster Types**           | Funding only              | 4 types (Hybrid Strong/Weak, Temporal, Funding) |
| **Behavioral Analysis**     | Basic                     | Advanced pattern matching                       |
| **Performance**             | Slower                    | Optimized with caching                          |
| **False Positive Handling** | Minimal                   | Built-in filters and thresholds                 |
| **Output Format**           | Flat groups               | Hierarchical risk-based clusters                |

### 📊 How It Works

#### Detection Methods

The system analyzes multiple dimensions to identify suspicious wallet clusters:

**1. Temporal Analysis ⏱️**

* Detects wallets that made their first trade within minutes of each other
* Identifies synchronized trading patterns
* Flags coordinated market entries
* Time windows: typically within short periods for high correlation

**2. Funding Analysis 💰**

* Traces wallet funding sources back to common origins
* Identifies shared funding patterns (CEX, mixers, stealth funding)
* Analyzes funding time proximity
* Detects sophisticated evasion techniques

**3. Behavioral Analysis 👥**

* Examines trading patterns across wallets
* Identifies coordinated holding/selling behavior
* Analyzes wallet age and activity history
* Detects similar buy amounts and timing

**4. Wallet Composition 🔍**

* Categorizes wallets as:
  * **New Wallets**: Created recently (high risk if many)
  * **Sniper Wallets**: Specialized in early token purchases
  * **Regular Wallets**: Normal trading history
  * **Unknown**: Insufficient data

### 🚨 Risk Scoring System

#### Overall Risk Score

Each cluster receives a risk score from 0-100%:

* 🔴 **70-100%**: VERY HIGH - Strong evidence of coordination
* 🟡 **40-69%**: HIGH - Likely coordinated activity
* 🟠 **20-39%**: MEDIUM - Some suspicious patterns
* 🟢 **0-19%**: LOW/MINIMAL - Normal activity

<figure><img src="https://2821085361-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2Fhfezr3vquyRvyuNwhInx%2Fuploads%2Fxlzn74rmjSAGi67hLHd8%2Fimage.png?alt=media&amp;token=ec8461de-3b78-44d6-9d69-7f851ed975b2" alt=""><figcaption></figcaption></figure>

#### Risk Factor Breakdown

The total risk score is composed of four weighted factors:

1. **Temporal Score (0-40%)**: How synchronized are first trades?
2. **Funding Score (0-50%)**: Do wallets share funding sources?
3. **Wallet Composition Score (0-25%)**: What types of wallets are involved?
4. **Behavioral Score (0-20%)**: How similar are trading patterns?

<figure><img src="https://2821085361-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2Fhfezr3vquyRvyuNwhInx%2Fuploads%2FOW1GsG40wf2IyG9aK6Bf%2Fimage.png?alt=media&amp;token=e527a4da-a38a-4a48-bac5-c690d6611276" alt=""><figcaption></figcaption></figure>

#### Confidence Levels

Each risk assessment comes with a confidence rating:

* ⚡ **Very High**: Multiple strong signals detected
* 🔥 **High**: Clear evidence patterns
* ⚠️ **Medium**: Notable indicators present
* 📊 **Low**: Weak signals
* ✓ **Minimal**: Insufficient evidence

### 🎯 Cluster Types

#### Hybrid Strong ⚡

* Both temporal AND funding evidence present
* Highest risk category
* Strong indication of coordinated activity

#### Hybrid Weak 🔄

* Mixed evidence from multiple sources
* Moderate to high risk
* Some wallets show temporal correlation, others show funding links

#### Temporal Only ⏱️

* Wallets traded at nearly the same time
* No shared funding detected
* Could indicate coordinated buying or coincidence

#### Funding Only 💰

* Wallets share common funding sources
* No temporal correlation
* May indicate same actor or service

### 🔴 Red Flags to Watch For

#### Critical Warning Signs:

1. **High New Wallet Percentage (>60%)**
   * Many wallets created just for this token
   * Strong indicator of artificial activity
2. **Tight Temporal Clustering**
   * Multiple wallets trading within minutes
   * Suggests automated or coordinated execution
3. **Stealth Funding Techniques 🥷**
   * Wallets using mixer services
   * Complex funding chains to obscure origins
   * Multiple hops through intermediate wallets
4. **High Supply Concentration**
   * Top 20 holders control >80% of supply
   * Risk of price manipulation
5. **Wash Trading Indicators**
   * Groups buying >100% of supply (recycling tokens)
   * Very low retention rates (<20%)
   * High volume with minimal price impact

### 📈 Understanding the Metrics

#### Supply Metrics

* **Supply Bought**: Total percentage of token supply purchased by the cluster
* **Supply Held**: Current holdings as percentage of total supply
* **Retention**: Percentage of bought tokens still held
* **Volume**: Total SOL spent by the cluster

<figure><img src="https://2821085361-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2Fhfezr3vquyRvyuNwhInx%2Fuploads%2Fq1qkNPJeOR3IajFNqw8T%2Fimage.png?alt=media&amp;token=369f3634-375e-4a80-a587-54f34d733aa4" alt=""><figcaption></figcaption></figure>

#### Temporal Metrics

* **Time Span**: Minutes between first and last wallet's first trade
* **Funding Sync**: How closely funding times align
* **Trade Sync**: How closely trading times align

#### Funding Metrics

* **Funding Sources**: Number of unique funding origins
* **Funding Time**: How recently wallets were funded
* **Connection Type**: SOL transfers, token transfers, or both

<figure><img src="https://2821085361-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2Fhfezr3vquyRvyuNwhInx%2Fuploads%2FHzYaOF5DLpHConkzIaDB%2Fimage.png?alt=media&amp;token=27a71cfe-533f-4379-bded-b1e1835e3f5c" alt=""><figcaption></figcaption></figure>

### ⚠️ Important Considerations

#### False Positives

The system may flag legitimate activity in certain cases:

* Multiple users withdrawing from the same CEX
* Popular wallet services or bots
* Coincidental timing during high-activity periods

#### Data Limitations

* Analysis is limited to on-chain data
* Recent tokens may have incomplete data
* Some sophisticated evasion techniques may go undetected

#### Best Practices

1. **Never rely on a single metric** - Consider the full picture
2. **Verify on-chain** - Check wallet activity on Solscan
3. **Consider context** - Token age, market conditions, etc.
4. **Look for patterns** - Multiple red flags are more concerning

### 🛡️ How to Use BRI for Due Diligence

#### Step-by-Step Process:

1. **Check Overall Risk Score**
   * Below 20%: Generally safe
   * 20-40%: Proceed with caution
   * Above 40%: High risk, investigate further
2. **Examine Risk Factors**
   * Which factors contribute most to the score?
   * Are there stealth funding indicators?
3. **Review Cluster Details**
   * How many wallets are involved?
   * What percentage of supply do they control?
   * What's their retention rate?
4. **Investigate Individual Wallets**
   * Click wallet addresses to view on Solscan
   * Check transaction history
   * Look for patterns across wallets
5. **Consider Market Impact**
   * Can these clusters dump the price?
   * Are they still accumulating?
   * What's their trading pattern?

### 🚀 Advanced Features

#### Stealth Detection

The system specifically identifies:

* Mixer usage
* Multi-hop funding chains
* Deliberate obfuscation techniques
* Time-delayed funding patterns

#### Temporal Correlation Scoring

Advanced algorithm that weighs:

* Funding-to-trading time gaps
* Cluster formation tightness
* Cross-wallet synchronization

### 📝 Glossary

* **Bundle**: Group of transactions executed together
* **Cluster**: Group of related wallets
* **Stealth Funding**: Techniques to hide funding origins
* **Temporal Correlation**: Time-based relationship between events
* **Wash Trading**: Buying and selling to create fake volume
* **Sybil Attack**: Using multiple wallets to appear as many users
* **CEX**: Centralized Exchange
* **Mixer**: Service that obscures transaction origins

### 🔧 Technical Details

#### Data Sources

* On-chain transaction data from Solana
* Token holder snapshots
* Historical trading data from DEXs
* Funding transfer analysis

#### Analysis Timeframes

* Funding analysis: Up to 100 days historical, with many hops and stealthy funding methods (account seeding, ATA closing, etc) tracked and flagged clearly.&#x20;
* Data refresh: Every 60 seconds (cached)

#### Performance

* Analysis time: Typically 5-30 seconds
* Can process up to 10,000 wallets
* Analyzes up to 25,000 transactions

### ❓ Frequently Asked Questions

**Q: What does >100% supply bought mean?** A: This indicates wash trading where the same tokens are being bought and sold repeatedly to inflate volume.

**Q: How accurate is the risk scoring?** A: The system has high accuracy for detecting coordinated activity, but always verify findings with additional research.

**Q: Can legitimate trading trigger high risk scores?** A: Yes, especially when multiple users withdraw from the same CEX or use the same trading bot.

**Q: What should I do if a token has high risk scores?** A: Investigate further, check individual wallets, and consider the risk in your investment decision.

**Q: How often is the data updated?** A: Real-time analysis with 1-minute caching to prevent overload.

### 📞 Support & Feedback

For questions, issues, or feedback about the Bundle Risk Index:

* Report issues directly to @maroon280 on telegram.&#x20;
* Use `/clusters help` in the bot for quick reference

***

*The Bundle Risk Index is a risk assessment tool. Always conduct your own research and due diligence before making investment decisions.*
