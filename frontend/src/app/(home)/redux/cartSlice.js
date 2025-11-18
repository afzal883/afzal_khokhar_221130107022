'use client';

import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';
import Cookies from 'universal-cookie';
import { addToast } from './toastSlice';
import { loader } from './loaderSlice';
import CryptoJS from 'crypto-js';
import  secureLocalStorage  from  "react-secure-storage";
import { setRedirect } from './redirectSlice';

const cookies = new Cookies();
const url = process.env.API_URL;

const SECRET_KEY = process.env.COOKIE_SECRET || 'default_secret_key';

// Utility: Encrypt data
const encryptData = (data) => {
    return CryptoJS.AES.encrypt(JSON.stringify(data), SECRET_KEY).toString();
};
// Utility: Decrypt data
const decryptData = (encryptedData) => {
    try {
        const bytes = CryptoJS.AES.decrypt(encryptedData, SECRET_KEY);
        return JSON.parse(bytes.toString(CryptoJS.enc.Utf8));
    } catch (error) {
        console.error('Decryption failed:', error); 
        return [];
    }
};

// Utility: Save to cookies
const saveToSession = (data) => {
    const encryptedData = encryptData(data);
    secureLocalStorage.setItem("cart_hashData", encryptedData)
};

export const fetchCart = createAsyncThunk('cart/fetchCart', async () => {
    const token = cookies.get('token');
    
    if (!token) {
        const encodedData = secureLocalStorage.getItem("cart_hashData")
        const data = decryptData(encodedData)
        return data.length > 0 ? data : []
    } else {
        try {
            const response = await fetch(`${url}/cart/`, {credentials:"include", method: "GET" });
            const json = await response.json()
            if (json.success) {
                return json.cart_items; // Return the user data
            } else {
                console.log(json.message || 'Failed to fetch user');
                return []
            }
        } catch (error) {
            console.error('Internal server error:', error);
            return []
        }
    }   
});

export const addToCart = createAsyncThunk(
    'cart/addToCart',
    async ({quantity, variant_data}, { rejectWithValue, dispatch, getState }) => {
        dispatch(loader(true))
        const token = cookies.get('token')
        const var_id = variant_data.id
        
        if(!token){
            try {
                
                const state = getState();
                let cartItems = state.cart.cart; // Assuming cart items are stored in `state.cart.items`
                
                const isItemInCart = cartItems.some(item => item.variant.id === var_id);
                if(isItemInCart){
                    await dispatch(increaseQty({id: var_id, quantity: quantity})); // Call increaseQty if item exists in the cart
                    dispatch(cartDrawer(true))
                    return rejectWithValue('Item quantity increased');
                }

                const data = { variant: variant_data, quantity: quantity };

                const finalData = [...cartItems, data]
                saveToSession(finalData)
                dispatch(addToast({ message: "Product Added To Cart", type: 'success' }));
                return {cart: data, quantity: quantity};

            } catch (error) {
                console.log(error);
            } finally{
                dispatch(loader(false))
            }
        } else { 
            try {
                
                const state = getState();
                const cartItems = state.cart.cart; // Assuming cart items are stored in `state.cart.items`

                // Check if the item is already in the cart
                if (cartItems) {
                    const isItemInCart = cartItems.some(item => item.variant.id === var_id);
                    if (isItemInCart) {
                        await dispatch(increaseQty({id: var_id, quantity: quantity})); // Call increaseQty if item exists in the cart
                        dispatch(cartDrawer(true))
                        return rejectWithValue('Item quantity increased');
                    }
                }

                const response = await fetch(
                    `${url}/add-to-cart/${var_id}/?quantity=${quantity}`,
                    { credentials:"include",
                        method: "POST"
                    }
                );
                const json = await response.json()
                if (response.ok && json.success) {
                    // If the API call is successful, add a success toast and return the cart
                    dispatch(addToast({ message: json.message, type: 'success' }));
                    return {cart: json.cart, quantity: quantity};
                } else {
                    // Handle other failure cases
                    dispatch(
                        addToast({
                            message: json.message || 'Failed to add item to cart',
                            type: 'error',
                        })
                    );
                    dispatch(setRedirect(`/login/`)); // Set redirect to Dashboard
                    return rejectWithValue(json.message || 'Unknown error occurred');
                }
            } catch (error) {
                dispatch(addToast({ message: error.message, type: 'error' }));
                return rejectWithValue(error.message);
            } finally {
                dispatch(loader(false))
            }
        }
    }
);

export const increaseQty = createAsyncThunk(
    'cart/increaseQty',
    async ({id, quantity}, { rejectWithValue, dispatch, getState }) => {
        dispatch(loader(true))
        const token = cookies.get('token');

        if(!token){
            try {
                    
                const state = getState();
                let cartItems = state.cart.cart; // Assuming cart items are stored in `state.cart.items`
                const updatedCart = cartItems.map(item => {
                    if (item.variant.id === id) {
                        if (item.quantity < item.variant.stock){
                            return { ...item, quantity: item.quantity + quantity }; // Increase quantity
                        }
                    }
                    return item;
                });
                
                saveToSession(updatedCart)
                return { id, quantity, success: true };
                
            } catch (error) {
                console.log(error);
            } finally{
                dispatch(loader(false))
            }
        } else {
            try {
                const response = await fetch(`${url}/plus-cart/${id}/?quantity=${quantity}`, {credentials:"include", method: 'POST' });
                const json = await response.json()
                if (json.success) {
                    // dispatch(addToast({ message: 'Quantity increased!', type: 'success' }));
                    return { id, quantity, success: true };
                } else {
                    if(response.status === 404){
                        dispatch(setRedirect(`/login/`)); // Set redirect to Dashboard
                    }
                    dispatch(
                        addToast({
                            message: json.message || 'Failed to add item to cart',
                            type: 'error',
                        })
                    );
                }
            } catch (error) {
                dispatch(addToast({ message: error.message, type: 'error' }));
                return rejectWithValue(error.message);
            } finally {
                dispatch(loader(false))
            }
        }
    }
);

export const decreaseQty = createAsyncThunk(
    'cart/decreaseQty',
    async (id, { rejectWithValue, dispatch, getState }) => {
        dispatch(loader(true))
        const token = cookies.get('token');

        
        if(!token){
            try {
                    
                const state = getState();
                let cartItems = state.cart.cart; // Assuming cart items are stored in `state.cart.items`
                let updatedCart = cartItems.map(item => {
                    if (item.variant.id === id) {
                                                    
                        return { ...item, quantity: item.quantity - 1 }; // Increase quantity
                    }
                    return item;
                });
                
                saveToSession(updatedCart)
                return { id, success: true };
                
            } catch (error) {
                console.log(error);
            } finally{
                dispatch(loader(false))
            }
        } else {
            try {
                const response = await fetch(`${url}/minus-cart/${id}/`, { credentials:"include",method: 'POST' });
                const json = await response.json()
                if (json.success) {
                    // dispatch(addToast({ message: 'Quantity decreased!', type: 'success' }));
                    return { id, success: true };
                } else {
                    dispatch(setRedirect(`/login/`)); // Set redirect to Dashboard
                    dispatch(
                        addToast({
                            message: json.message || 'Failed to add item to cart',
                            type: 'error',
                        })
                    );
                }
            } catch (error) {
                dispatch(addToast({ message: error.message, type: 'error' }));
                return rejectWithValue(error.message);
            } finally {
                dispatch(loader(false))
            }
        }

        
    }
);
export const setQty = createAsyncThunk(
    'cart/setQty',
    async ({ id, quantity }, { rejectWithValue, dispatch, getState }) => {
        dispatch(loader(true));
        const token = cookies.get('token');

        if (!token) {
            try {
                const state = getState();
                let cartItems = state.cart.cart;

                const updatedCart = cartItems.map(item => {
                    if (item.variant.id === id) {
                        if (quantity < item.variant.stock){
                            return { ...item, quantity }; // Set new quantity directly
                        }
                    }
                    return item;
                });

                saveToSession(updatedCart);
                return { id, quantity, success: true };

            } catch (error) {
                console.log(error);
            } finally {
                dispatch(loader(false));
            }
        } else {
            try {
                const response = await fetch(`${url}/set-cart/${id}/?quantity=${quantity}`, {
                    credentials:"include",
                    method: 'POST',
                });

                const json = await response.json();
                if (json.success) {
                    return { id, quantity, success: true };
                } else {
                    dispatch(setRedirect(`/login/`));
                    dispatch(
                        addToast({
                            message: json.message || 'Failed to set quantity',
                            type: 'error',
                        })
                    );
                }
            } catch (error) {
                dispatch(addToast({ message: error.message, type: 'error' }));
                return rejectWithValue(error.message);
            } finally {
                dispatch(loader(false));
            }
        }
    }
);


export const removeFromCart = createAsyncThunk(
    'cart/removeFromCart',
    async (id, { rejectWithValue, dispatch, getState }) => {
        dispatch(loader(true))
        const token = cookies.get('token');

        if(!token){
            try {
                    
                const state = getState();
                let cartItems = state.cart.cart; // Assuming cart items are stored in `state.cart.items`
                const updatedCart = cartItems.filter((item) => item.variant.id !== id);

                saveToSession(updatedCart)
                return { id, success: true };
                
            } catch (error) {
                console.log(error);
            } finally{
                dispatch(loader(false))
            }
        } else {
            try {
                const response = await fetch(`${url}/remove-from-cart/${id}/`, { credentials:"include", method: 'DELETE' });
                const json = await response.json()
                if (json.success) {
                    dispatch(addToast({ message: 'Item removed from cart!', type: 'success' }));
                    return { id, success: true };
                } else {
                    throw new Error(json.message || 'Failed to remove item');
                }
            } catch (error) {
                dispatch(addToast({ message: error.message, type: 'error' }));
                return rejectWithValue(error.message);
            } finally {
                dispatch(loader(false))
            }
        }

        
    }
);

// Slice
const cartSlice = createSlice({
    name: 'cart',
    initialState: {
        cart: [],
        total: 0,
        status: 'idle',
        error: null,
        openCart: false,
    },
    reducers: {
        cartDrawer: (state, action) => {
            state.openCart = action.payload;
        },
        setCartItems: (state, action) => {
            state.cart = action.payload
        },
        setTotal: (state, action) => {
            state.total = action.payload
        }
    },
    extraReducers: (builder) => {
        builder
            // Fetch cart
            .addCase(fetchCart.pending, (state) => {
                state.status = 'loading';
            })
            .addCase(fetchCart.fulfilled, (state, action) => {
                state.status = 'succeded';
                state.cart = action.payload === "undefined" ? [] : action.payload;
                state.total = action.payload && action.payload.reduce((total, item) => total + item.variant.discounted_price * item.quantity, 0);
            })
            .addCase(fetchCart.rejected, (state, action) => {
                state.status = 'failed';
                state.error = action.payload;
            })

            // Add to cart
            .addCase(addToCart.fulfilled, (state, action) => {
                state.cart.push(action.payload.cart);
                state.total = state.total + JSON.parse(action.payload.cart.variant.discounted_price) * action.payload.quantity
                state.openCart = true;
            })
            // Increase quantity
            .addCase(increaseQty.fulfilled, (state, action) => {
                const item = state.cart.find((item) => item.variant.id === action.payload.id);
                if (item) {
                    if(item.quantity<item.variant.stock){
                        item.quantity += action.payload.quantity;
                        state.total = state.total + JSON.parse(item.variant.discounted_price) * action.payload.quantity
                    }
                }
            })
            // Decrease quantity
            .addCase(decreaseQty.fulfilled, (state, action) => {
                const item = state.cart.find((item) => item.variant.id === action.payload.id);
                if (item && item.quantity > 1) {
                    item.quantity -= 1;
                    state.total = state.total - JSON.parse(item.variant.discounted_price)
                }
            })
            .addCase(setQty.fulfilled, (state, action) => {
                const item = state.cart.find(item => item.variant.id === action.payload.id);
                if (item) {
                    const oldQty = item.quantity;
                    if (action.payload.quantity <item.variant.stock){
                        item.quantity = action.payload.quantity;
                        const diff = action.payload.quantity - oldQty;
                        state.total += JSON.parse(item.variant.discounted_price) * diff;
                    }
                }
            })

            // Remove from cart
            .addCase(removeFromCart.fulfilled, (state, action) => {
                const item = state.cart.find((item) => item.variant.id === action.payload.id);
                if(item){
                    state.cart = state.cart.filter((item) => item.variant.id !== action.payload.id);
                    state.total = state.total - item.variant.discounted_price * item.quantity
                }
            });
    },
});

// Export actions
export const { cartDrawer, setCartItems, setTotal } = cartSlice.actions;

// Selectors
export const selectCart = (state) => state.cart;
export const selectCartStatus = (state) => state.status;
export const selectCartError = (state) => state.error;

// Reducer
export default cartSlice.reducer;