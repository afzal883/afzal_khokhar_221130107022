import React from 'react'
import Checkout from './Checkout'
import { cookies } from 'next/headers'
import CryptoJS from 'crypto-js'

export const metadata = {
  alternates: {
    canonical: `https://www.hidelifestyle.co.uk/checkout/`,
  }
};

const decryptData = (encryptedData) => {
  try {
    const SECRET_KEY = process.env.COOKIE_SECRET || 'default_secret_key';
    const bytes = CryptoJS.AES.decrypt(encryptedData, SECRET_KEY);
    return JSON.parse(bytes.toString(CryptoJS.enc.Utf8));
  } catch (error) {
    console.error('Decryption failed:', error);
    return null;
  }
};

const getCheckoutSource = () => {
  const cookieStore = cookies();
  const encryptedData = cookieStore.get('checkout_source')?.value;
  if (!encryptedData) return null;
  return decryptData(encryptedData);
};

const getCheckoutData = () => {
  const cookieStore = cookies();
  const encryptedData = cookieStore.get('checkout_hashData')?.value;
  if (!encryptedData) return null;
  return decryptData(encryptedData);
};

const fetchServerCart = async () => {
  const cookieStore = cookies();
  const token = cookieStore.get('token')?.value;
  
  if (!token) {
    // Handle guest checkout from cookies (similar to loadCheckout logic)
   return null
  } else {
    // Handle authenticated user cart
    try {
      const response = await fetch(`${process.env.API_URL}/cart/`, {
        credentials: "include",
        headers: {
          'Authorization': `Bearer ${token}`,
          'Cookie': cookieStore.toString()
        },
      });
      const json = await response.json();

      return json.success ? json.cart_items : [];
    } catch (error) {
      console.error('Error fetching cart:', error);
      return [];
    }
  }
};

const calculateCheckoutTotals = async (source, cartData, promoCode = '') => {
  try {
    const response = await fetch(`${process.env.API_URL}/checkout-total/?source=${source}`, {
      method: "POST",
      credentials:"include",
      headers: {
        "Content-Type": "application/json",
        "Cookie": cookies().toString()
      },
      body: JSON.stringify({
        promo_code: promoCode,
        cart_data: source === "cart" ? cartData : { item: cartData.item, quantity: cartData.quantity },
        source,
        cod:"ONLINE"
      }),
    });
    return await response.json();
  } catch (error) {
    console.error("Error calculating totals:", error);
    return null;
  }
};

const page = async () => {
  const source = getCheckoutSource();
  const cookieStore = cookies();
  const token = cookieStore.get('token')?.value;

  let cartData = null;
  let totals = null;
  
  if (source === 'cart') {
    cartData = await fetchServerCart();

    
    if(cartData!=null){
      if (cartData.length > 0) {
        totals = await calculateCheckoutTotals(source, cartData,"");
      }
    }
    else{
      totals = null
    }
  } else if (source==="buynow") {
    cartData = getCheckoutData();
    if (cartData) {
      totals = await calculateCheckoutTotals(source, cartData,"");
    }
  }

  return (
    <Checkout
      serverSource={source && source}
      serverCartItems={source === 'cart' ? cartData : null}
      serverBuyNowItems={source !== 'cart' ? cartData : null}
      serverTotals={totals}
      token={token}
    />
  )
}

export default page