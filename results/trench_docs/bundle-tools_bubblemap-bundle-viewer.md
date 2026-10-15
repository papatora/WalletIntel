> For the complete documentation index, see [llms.txt](https://docs.trench.bot/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://docs.trench.bot/bundle-tools/bubblemap-bundle-viewer.md).

# Bubblemap Bundle Viewer

This is a brief guide on our bubblemap bundle viewer website hosted at https\://trench.bot/!

Viewing bundles in telegram can give critical insights about a token and allow you to buy quickly. However, there are limits to how much we can cram into one simple message, and most the time we end up missing important data. \
\
This is where the idea of a bubblemap-like viewer sprouted. It simply made sense to be able to see the full data for any token and see who's actually part of a bundle easily. \
\
Initially this was a scrapped project as there was no time to complete it, but our friend [OtterOlie](https://x.com/otterolie) stepped in and actually helped finish up and polish the idea from the existing code. Show him some love!\
\
This tool will allow you to view bundles to a full extent, so that you can see if it's actually the team being devious or if it's some random snipers or copy traded wallets. Here's a quick guide written by otter!

## TrenchRadar Bundle Viewer

TrenchRadar Bundle Viewer is a Solana token bundle visualization tool tailored specifically for **Pump.fun** tokens. This tool allows users to track token distributions and explore holdings across various wallets and bundles through an intuitive, interactive bubble map.

> **Note**: TrenchRadar only supports **Pump.fun** tokens. Therefore, ensure that the Solana address entered ends with **"pump"**.

### Key Features

* **Interactive Bubble Map**: Visualize token bundles with bubbles representing the holding percentage of each bundle. Color-coded bubbles clearly show the difference between "Holding" and "Sold" tokens.
* **Bundle Details**: Click any bubble to view specific bundle details, including the total SOL, total tokens, unique wallets, and holding percentage.
* **Toggle for Empty Bundles**: Simplify your view by toggling the display of empty bundles on or off.
* **Zoom Controls**: Easily adjust the zoom to focus on individual bundles or view the entire distribution.
* **Screenshot to Clipboard**: Take instant screenshots of your bundle map. Just click the camera icon, and the screenshot will be saved directly to your clipboard.

### Getting Started

1. **Accessing the Viewer**: Go to <https://trench.bot> and paste a Solana address ending with **"pump"** into the search bar.
2. **Viewing Bundles**: Click on "View Bundles" to load and visualize the bundle data for your address.
3. **Using the Show Empty Bundles Toggle**: Use this toggle to hide or show empty bundles for a cleaner view (by default, this is turned off).
4. **Taking Screenshots**: Click the camera icon in the top-left corner to capture the current view. The screenshot is automatically copied to your clipboard and also downloaded.
5. **Zoom Controls**: Use the "+" and "−" buttons to zoom in or out on the bundle map.

### User Interface Breakdown

* **Input Field**: Paste a Solana address ending with **"pump"** here.
* **View Bundles Button**: Click to load the data for the entered bundle address.
* **Refresh Button:** Click to refresh your currently displayed token to get new info&#x20;

#### 2. Bubble Map

* **Holding vs. Sold**: Bubbles are color-coded—red for "Holding" and gray for "Sold."
* **Bubble Sizes**: Each bubble represents a bundle, with the size reflecting the token holding percentage.
* **Hover Details**: Hover over bubbles to see individual holding percentages.
* **Show Empty Bundles Toggle**: Switch on/off to reveal or hide empty bundles.

#### 3. Legend

* **Holding**: Represented in red.
* **Sold**: Represented in gray.

#### 4. Screenshot Button

* **Camera Icon**: Located in the top-left corner of the map, the camera icon allows you to capture the current view as a screenshot directly to your clipboard.

#### 5. Bundle Information Pop-Up (when you click on %)

* **Total SOL**: Displays the total SOL amount within the bundle.
* **Total Tokens**: Shows the total number of tokens in the bundle.
* **Unique Wallets**: Lists the number of unique wallets holding tokens in this bundle.
* **Holding Percentage**: Indicates the overall percentage held.
* **Wallet Information**: Shows each wallet's share within the bundle.

### Frequently Asked Questions (FAQ)

#### 1. How do I hide bundles with no holdings?

* Use the “Show Empty Bundles” toggle on the top right to hide or display empty bundles.

#### 2. How do I interpret the holding percentages?

* Each bubble's size represents the percentage of tokens held within that bundle. Click on a bubble to get more detailed information.

#### 3. Can I view bundle details for individual wallets?

* Yes, click on a bubble to open the Bundle Information pop-up, which shows a breakdown of wallets within that bundle.

#### 4. Why isn't my Solana address loading?

* Ensure that the Solana address you entered ends with **"pump"**, as TrenchRadar currently only supports **Pump.fun** tokens.

#### 5. How do I capture a screenshot?

* Click the camera icon in the top-left corner of the map. The screenshot will be copied directly to your clipboard and also downloaded in one click

### Troubleshooting

* **Empty Bubble Map**: Verify that your address ends with **"pump"** and ensure it’s a valid Pump.fun token address. If all tokens have been sold, toggle the "Show Empty Bundles" option to see empty bundles.
* **Incorrect Bundle Data**: Confirm that the bundle address is correct and ends with **"pump"**.

***

* **Backend**: Bahr
* **Frontend**: OtterOlie
