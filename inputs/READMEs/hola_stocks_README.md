# Stock Ticker Data Visualizer

This web application allows users to interact with a dataset comprised of stock ticker data via meaningful data visualizations. Users can choose stock tickers, visualize closing prices, daily returns, candlestick charts, and moving averages over different periods.

## Features  

- **Interactive Visualization**: Users can select stock tickers and visualize closing prices, daily returns, candlestick charts, and moving averages.  
- **Multiple Ticker Support**: Users can track and visualize multiple stock tickers during a session.  
- **Alpha Vantage API Integration**: Real-time stock data is fetched using the Alpha Vantage API.  
- **Diverse Visualizations**: Provides a range of visualizations to help users understand stock performance patterns over time.  
 
## Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/your-username/stock-ticker-visualizer.git
```  

2. Install the required dependencies:  
   ```bash
   pip install -r requirements.txt
```  

3. Setup your Alpha Vantage API key:
Replace YOUR_API_KEY in the code with your actual Alpha Vantage API key.


4. Run the Streamlit app:
```
streamlit run app.py
```


## Usage
* Enter a stock symbol in the sidebar to fetch and visualize the stock data.  
* Select multiple stock tickers to compare their performance.  
* Choose different visualizations (closing prices, daily returns, candlestick charts, moving averages) using the sidebar options.  

## Technologies Used
Python
Streamlit
Alpha Vantage API
Plotly

## Acknowledgements
This project uses data from the Alpha Vantage API.
The visualizations are created using Plotly.
Built with Streamlit for the interactive web application.

## License
This project is licensed under the MIT License - see the LICENSE file for details.

