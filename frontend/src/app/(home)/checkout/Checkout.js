"use client";
import React, { useEffect, useState } from "react";
import styles from "@/app/(home)/styles/checkout.module.css";
import Cart from "@/app/(home)/styles/cart.module.css";
import Image from "next/image";
import Link from "next/link";
import { IoCloseOutline } from "react-icons/io5";
import { useDispatch } from "react-redux";
import { useSelector } from "react-redux";
import { fetchCart, selectCart } from "../redux/cartSlice";
import {
  addCheckoutItem,
  loadCheckout,
  selectCheckoutItems,
  setCheckoutItems,
} from "../redux/checkoutSlice";
import { useForm } from "react-hook-form";
import { loader } from "../redux/loaderSlice";
import Cookies from "universal-cookie";
import { addToast } from "../redux/toastSlice";
import { usePathname, useRouter } from "next/navigation";
import { loadStripe } from "@stripe/stripe-js";
import { fetchAddresses } from "../redux/userSlice";
import { GoGift } from "react-icons/go";
import CryptoJS from "crypto-js";
import Razorpay from "razorpay";
import { Country, State, City } from "country-state-city";
import Select from "react-select";
import { customStyles } from "../components/CustomeSelectStyles";

const Checkout = ({
  serverSource,
  serverBuyNowItems,
  serverCartItems,
  serverTotals,
  token,
}) => {
  const dispatch = useDispatch();
  const router = useRouter();
  const pathname = usePathname();
  const cookies = new Cookies();
  // Redux selectors
  const { cart } = useSelector(selectCart);
  const { addresses, user } = useSelector((state) => state.user);
  const [initialized, setInitialized] = useState(false);
  // State management
  const source = serverSource;
  const items = source === "cart" ? serverCartItems || cart : serverBuyNowItems;

  const [promoCode, setPromoCode] = useState("");
  const [promoApplied, setPromoApplied] = useState(false);
  const [error, setError] = useState(null);
  const [country, setCountry] = useState("+91");
  const [selectedAddress, setSelectedAddress] = useState(null);
  const [discount_type, setDiscount_type] = useState(null);
  const [amount, setAmount] = useState(
    serverTotals?.amount || {
      original_price: 0,
      sub_total: 0,
      shipping: 0,
      discount: 0,
      tax_rate: 0,
      tax: 0,
      total: 0,
    }
  );
  const india = Country.getAllCountries().find((c) => c.name === "India");
  const [selectedCountry, setSelectedCountry] = useState({
    label: india.name,
    value: india.isoCode,
  });
  const [selectedState, setSelectedState] = useState(null);
  const [selectedCity, setSelectedCity] = useState(null);

  const countryOptions = Country.getAllCountries().map((country) => ({
    value: country.isoCode,
    label: country.name,
  }));
  const stateOptions = selectedCountry
    ? State.getStatesOfCountry(selectedCountry.value).map((state) => ({
        value: state.isoCode,
        label: state.name,
      }))
    : [];

  const cityOptions =
    selectedCountry && selectedState
      ? City.getCitiesOfState(selectedCountry.value, selectedState.value).map(
          (city) => ({
            value: city.name,
            label: city.name,
          })
        )
      : [];

  useEffect(() => {
    setValue("country", selectedCountry?.label || "");
    setValue("state", selectedState?.label || "");
    setValue("city", selectedCity?.label || "");
  }, [selectedCountry, selectedState, selectedCity]);
  const url = process.env.API_URL;

  // Form handling
  const {
    register,
    handleSubmit,
    setValue,
    getValues,
    watch,
    reset,
    formState: { errors },
  } = useForm({
    defaultValues: {
      pincode: "",
      paymentMethod: "ONLINE",
    },
  });
  useEffect(() => {
    if (serverTotals === null) {
      dispatch(fetchCart());
      setInitialized(true);
    }
  }, []);
  const pincode = watch("pincode");
  const paymentMethodType = watch("paymentMethod");

  // Data encryption/decryption utilities
  const decryptData = (encryptedData) => {
    try {
      const SECRET_KEY = process.env.COOKIE_SECRET || "default_secret_key";
      const bytes = CryptoJS.AES.decrypt(encryptedData, SECRET_KEY);
      return JSON.parse(bytes.toString(CryptoJS.enc.Utf8));
    } catch (error) {
      console.error("Decryption failed:", error);
      return null;
    }
  };

  const encryptData = (data) => {
    const SECRET_KEY = process.env.COOKIE_SECRET || "default_secret_key";
    return CryptoJS.AES.encrypt(JSON.stringify(data), SECRET_KEY).toString();
  };

  useEffect(() => {
    if (!initialized && serverSource) {
      if (!serverBuyNowItems || !serverCartItems) {
        dispatch(loadCheckout());
        setInitialized(true);
      }
    }
  }, [dispatch, initialized, serverSource, serverBuyNowItems]);
  // Fetch checkout totals
  const getCheckoutDetail = async () => {
    try {
      dispatch(loader(true));
      const currentFormData = getValues();

      const response = await fetch(`${url}/checkout-total/?source=${source}`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...currentFormData,
          promo_code: promoCode,
          source,
          cart_data:
            source === "cart" ? serverCartItems || cart : serverBuyNowItems,
          cod: 1,
        }),
      });

      const json = await response.json();
      if (json.success) {
        setAmount(json.amount);
        setDiscount_type(json.discount_type);
        if (json.message) {
          dispatch(addToast({ message: json.message, type: "success" }));
        }
      } else {
        dispatch(addToast({ message: json.message, type: "error" }));
      }
    } catch (e) {
      console.error("Error fetching checkout details:", e);
      router.push("/")
    } finally {
      dispatch(loader(false));
    }
  };
  useEffect(() => {
    if (
      initialized &&
      ((source === "cart" && cart.length) || (source !== "cart" && items?.item))
    ) {
      getCheckoutDetail();
    }
  }, [source, cart, items, initialized]);
  // Effects
  useEffect(() => {
    dispatch(fetchAddresses());
    // initializeCheckoutSource();
  }, [dispatch]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (pincode && pincode.length === 6) {
        if (paymentMethodType !== null) {
          getCheckoutDetail();
        }
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [pincode, paymentMethodType]);

  useEffect(() => {
    if (addresses?.length > 0) {
      setSelectedAddress(0);
      const defaultAddress = addresses[0];
      setSelectedCountry({ ...selectedCountry, label: defaultAddress.country });
      setSelectedState({ label: defaultAddress.state });
      setSelectedCity({ label: defaultAddress.city });
      Object.entries({
        address: defaultAddress.address,
        pincode: defaultAddress.pincode,
      }).forEach(([key, value]) => setValue(key, value || "")); 
    }
    setValue("name", user?.name)
    setValue("email", user?.email)
    setValue("phone", user?.phone_number)
  }, [addresses, setValue]);

  useEffect(() => {
    const data = sessionStorage.getItem("checkout_details");
    if (data) {
      try {
        const storedData = decryptData(data);
        setCountry(storedData.phone.split(" ")[0]);
        setSelectedState({ label: storedData.state });
        setSelectedCity({ label: storedData.city });
        reset({
          ...storedData,
          phone: storedData.phone.split(" ")[1],
        });
      } catch (error) {
        console.error("Error parsing stored data:", error);
      }
    }
  }, [reset]);

  // Handlers
  const removePromoCode = async () => {
    setPromoApplied(false);
    setPromoCode("");
    await getCheckoutDetail();
  };

  const handleSelectAddress = (item, index) => {
    setSelectedAddress(index);
    setSelectedCountry({ label: item.country });
    setSelectedState({ label: item.state });
    setSelectedCity({ label: item.city });
    Object.entries({
      address: item.address,
      pincode: item.pincode,
    }).forEach(([key, value]) => setValue(key, value));
  };

  async function createPayuURL(data) {
    const res = await fetch(process.env.API_URL + `/initiate-payment/?source=${source}`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data), // amount in paise
    });

    const json = await res.json();
    return json;
  }

  async function handlePayment(data) {
    try {
      const amt = amount?.total;
      data.amt = amt
      const paymentData = await createPayuURL(data);
      const url = paymentData?.payu_url;

      const form = document.createElement("form");
      form.method = "POST";
      form.action = url;

      console.log(paymentData);
      if(paymentData.params){
        Object.entries(paymentData.params).forEach(([key, value]) => {
          const input = document.createElement("input");
          input.type = "hidden";
          input.name = key;
          input.value = value;
          form.appendChild(input);
        });
  
        document.body.appendChild(form);
        form.submit();
      } else {
        console.error("params not found");
      }
    } catch (error) {
      console.error("🔥 Error during payment request:", error);
    }
  }

  const onSubmit = async (data) => {
    try {
      const checkoutData = {
        ...data,
        source,
        amount,
        product: source === "cart" ? serverCartItems : serverBuyNowItems,
        promo: { type: discount_type, code: promoCode },
        phone: `${country} ${data.phone}`,
        shipping: amount?.shipping,
      };

      sessionStorage.setItem("checkout_details", encryptData(checkoutData));
      dispatch(loader(true));

      if (!token) {
        router.replace("/login?redirect=/checkout");
        return;
      }

      // ONLINE payment -> redirect to PayU hosted page
      if (data.paymentMethod === "ONLINE") {
        await handlePayment(checkoutData);
        // If handlePayment succeeded it will have submitted the form and navigated away.
        // Execution probably won't reach here because page navigation happens.
        return;
      }
      // COD (or offline) flow: verify/create order on backend
      const verifyRes = await fetch(
        `${process.env.API_URL}/initiate-payment/?source=${source}`,
        {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(checkoutData),
        }
      );

      const json = await verifyRes.json();

      if (json.success) {
        router.replace(`/order-confirm?order_id=${json.order_id}`);
        dispatch(addToast({ message: json.message, type: "success" }));
        dispatch(fetchCart());
        cookies.remove("checkout_source");
      } else {
        dispatch(
          addToast({
            message: json.message || "Failed to place order",
            type: "error",
          })
        );
      }
    } catch (error) {
      console.error("onSubmit error:", error);
      setError(error?.message || "An error occurred during checkout");
      dispatch(
        addToast({
          message: "An error occurred during checkout",
          type: "error",
        })
      );
    } finally {
      dispatch(loader(false));
    }
  };

  function getProductURL(product) {
    const mainCategory = product.category.find((cat) => cat.level === 0);
    const subCategory = product.category.find((cat) => cat.level === 1);

    if (subCategory) {
      // We're on subcategory page → include both
      return `/${mainCategory.name
        .toLowerCase()
        .replace(/\s+/g, "-")}/${subCategory.name
        .toLowerCase()
        .replace(/\s+/g, "-")}/${product.slug}`;
    }

    // Otherwise just category/product-slug
    return `/${mainCategory.name.toLowerCase().replace(/\s+/g, "-")}/${
      product.slug
    }`;
  }

  const renderItem = ({ variant, quantity }, key) => {
    if (!variant) return null;

    const { product, encoded_sku, images, discounted_price } = variant;
    const imageUrl = images?.[0] ? process.env.IMAGE_URL + images[0].image : "";

    return (
      <div
        className={`${Cart.item} border-2 border-[rgb(0,0,0,0.1)]`}
        key={key}
      >
        <Link href={getProductURL(product)} className={Cart.image}>
          <Image
            src={imageUrl}
            width={200}
            height={200}
            alt=""
            className="img-fluid"
          />
        </Link>

        <div className={Cart.item_content}>
          <Link href={getProductURL(product)}>
            <h6>{product.title}</h6>
          </Link>

          <div className="my-3">
            <p className="uppercase">Price</p>
            <span className={Cart.price}>
              &#8377; {(discounted_price * quantity).toFixed(2)}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <div>
              <p className="uppercase">qty</p>
              <div className="text-center w-full">{quantity}</div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const returnItems = () => {
    if (source === "cart") {
      return Array.isArray(items) && items.length > 0
        ? items.map((item, index) => renderItem(item, index))
        : null;
    } else if (source === "buynow") {
      return items?.item
        ? renderItem({ variant: items.item, quantity: items.quantity }, 0)
        : null;
    } else {
      return null;
    }
  };

  return (
    <div className={`${styles.container} container-fluid padd-x`}>
      <form className="py-[2em]" onSubmit={handleSubmit(onSubmit)}>
        <div className={`${styles.container1} row`}>
          <div className={`${styles.section2} col-lg-4`}>
            <h1 className="">Checkout</h1>
            <div className={`${styles.cart} pt-4`}>
              <h4 className="mt-3 mb-3">Review your cart</h4>
              <div className={styles.cart_list}>{returnItems()}</div>
            </div>
          </div>
          <div className={`${styles.section1} col-lg-8 col-12`}>
            <h4 className="mb-3">Select a delivery address</h4>

            {addresses && addresses.length > 0 && (
              <div className={styles.addressContainer}>
                {addresses.map((item, index) => (
                  <label
                    htmlFor={`Address-${index}`}
                    key={index}
                    className={styles.addressItem}
                  >
                    <input
                      type="radio"
                      id={`Address-${index}`}
                      checked={selectedAddress === index}
                      onChange={() => handleSelectAddress(item, index)}
                      className={styles.customRadio}
                    />
                    <span className={styles.radioCircle}></span>
                    <div
                      className="d-flex align-items-start flex-column"
                      style={{ gap: ".5px" }}
                    >
                      <h6>{item.address}</h6>
                      <p>
                        {item.address}, {item.city}, {item.state},{" "}
                        {item.pincode}, {item.country}
                      </p>
                    </div>
                  </label>
                ))}
              </div>
            )}

            <div className=" border p-4 rounded ">
              <div className="row">
                <div className="col-12">
                  <div className="input-field">
                    <label htmlFor="name">Name</label>
                    <div className="input">
                      <input
                        type="text"
                        placeholder="Enter your Name"
                        id="name"
                        {...register("name", { required: "Name is required" })}
                      />
                    </div>
                    {errors.name && (
                      <span className="text-red-500 text-xs">
                        {errors.name.message}
                      </span>
                    )}
                  </div>
                </div>

                <div className="col-sm-6">
                  <div className="input-field">
                    <label htmlFor="email">Email Address</label>
                    <div className="input">
                      <input
                        type="email"
                        placeholder="Enter your Email"
                        id="email"
                        {...register("email", {
                          required: "Email is required",
                          pattern: {
                            value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                            message: "Invalid email address",
                          },
                        })}
                      />
                    </div>
                    {errors.email && (
                      <span className="text-red-500 text-xs">
                        {errors.email.message}
                      </span>
                    )}
                  </div>
                </div>

                <div className="col-sm-6">
                  <div className="input-field">
                    <label htmlFor="phone">Phone Number</label>

                    <div className="input">
                      <input
                        type="text"
                        placeholder="Enter your Phone Number"
                        id="phone"
                        {...register("phone", {
                          required: "Phone Number is required",
                          pattern: {
                            value: /^[0-9]{10}$/,
                            message: "Phone number must be 10 digits",
                          },
                        })}
                      />
                    </div>
                    {errors.phone && (
                      <span className="text-red-500 text-xs">
                        {errors.phone.message}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="input-field">
                <label htmlFor="address">Address</label>
                <div className="input">
                  <textarea
                    name="address"
                    id="address"
                    placeholder="Enter your Address"
                    rows={1}
                    {...register("address", {
                      required: "Address is required",
                    })}
                  ></textarea>
                </div>
                {errors.address && (
                  <span className="text-red-500 text-xs">
                    {errors.address.message}
                  </span>
                )}
              </div>

              <div className="row">
                <div className="col-sm-6 col-12">
                  <div className="input-field">
                    <label htmlFor="country">Country</label>
                    <div className="w-full">
                      <Select
                        id="country"
                        options={countryOptions}
                        value={selectedCountry}
                        onChange={(val) => {
                          setSelectedCountry(val);
                          setSelectedState(null);
                          setSelectedCity(null);
                        }}
                        isDisabled
                        styles={customStyles}
                        classNamePrefix="react-select"
                        placeholder="Select Country"
                      />
                    </div>

                    {errors.country && (
                      <span className="text-red-500 text-xs">
                        {errors.country.message}
                      </span>
                    )}
                  </div>
                </div>

                {/* State */}
                <div className="col-sm-6 col-12">
                  <div className="input-field">
                    <label htmlFor="state">State</label>
                    <div className="w-full">
                      <Select
                        id="state"
                        options={stateOptions}
                        value={selectedState}
                        onChange={(val) => {
                          setSelectedState(val);
                          setSelectedCity(null);
                        }}
                        styles={customStyles}
                        classNamePrefix="react-select"
                        placeholder="Select State"
                        isDisabled={!selectedCountry}
                      />
                    </div>
                    {errors.state && (
                      <span className="text-red-500 text-xs">
                        {errors.state.message}
                      </span>
                    )}
                  </div>
                </div>

                {/* City */}
                <div className="col-sm-6 col-12">
                  <div className="input-field">
                    <label htmlFor="city">City</label>
                    <div className="w-full">
                      <Select
                        id="city"
                        options={cityOptions}
                        value={selectedCity}
                        onChange={(val) => setSelectedCity(val)}
                        classNamePrefix="react-select"
                        placeholder="Select City"
                        styles={customStyles}
                        isDisabled={!selectedState}
                      />
                    </div>
                    {errors.city && (
                      <span className="text-red-500 text-xs">
                        {errors.city.message}
                      </span>
                    )}
                  </div>
                </div>
                <div className="col-sm-6 col-12">
                  <div className="input-field">
                    <label htmlFor="Pin-code">Pin Code</label>
                    <div className="input">
                      <input
                        type="text"
                        placeholder="Enter pin code"
                        id="Pin-code"
                        maxLength={6}
                        {...register("pincode", {
                          required: "Pincode is required",
                          pattern: {
                            value: /^\d{6}$/,
                            message: "Please enter a valid 6-digit pincode",
                          },
                          maxLength: {
                            value: 6,
                            message: "Pincode cannot be more than 6 digits",
                          },
                          minLength: {
                            value: 6,
                            message: "Pincode must be exactly 6 digits",
                          },
                        })}
                      />
                    </div>
                    {errors.pincode && (
                      <span className="text-red-500 text-xs">
                        {errors.pincode.message}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
            <div className={`${styles.payment}  py-4  rounded mt-3`}>
              <div className="w-full  ">
                <h5 className="text-xl font-semibold mb-4">Payment Method</h5>

                <div className="input-field">
                  <div className="input">
                    <i className="mr-4">
                      <GoGift />{" "}
                    </i>
                    <input
                      type="text"
                      placeholder="Discount code or Gift card"
                      id="code"
                      value={promoCode}
                      onChange={(e) => setPromoCode(e.target.value)}
                      readOnly={promoApplied} // Make input read-only if promo applied
                    />
                    {promoApplied ? (
                      <div className="promo-applied d-flex align-items-center">
                        <button
                          type="button"
                          className="remove-btn"
                          onClick={removePromoCode}
                        >
                          <IoCloseOutline />
                        </button>
                      </div>
                    ) : (
                      <button
                        disabled={promoCode === ""}
                        type="button"
                        onClick={() => {
                          getCheckoutDetail(cart, items);
                        }}
                      >
                        Apply
                      </button>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Payment Method Selection */}
                  <div className="border p-4 ">
                    <h6 className="text-lg font-medium mb-3">
                      Choose Payment Type
                    </h6>

                    <div className="space-y-3">
                      <label className="flex items-center cursor-pointer">
                        <input
                          type="radio"
                          value="ONLINE"
                          {...register("paymentMethod", {
                            required: "Please select a payment method",
                          })}
                          className="form-radio h-5 w-5 text-blue-600"
                        />
                        <span className="ml-3 text-sm font-medium">
                          Pay Online (UPI / Card / NetBanking)
                        </span>
                      </label>

                      {/* <label className="flex items-center cursor-pointer">
                        <input
                          type="radio"
                          value="COD"
                          {...register("paymentMethod")}
                          className="form-radio h-5 w-5 text-blue-600"
                        />
                        <span className="ml-3 text-sm font-medium">
                          Cash on Delivery (COD)
                        </span>
                      </label> */}

                      {errors.paymentMethod && (
                        <p className="text-red-500 text-sm">
                          {errors.paymentMethod.message}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Order Summary */}
                  <div className="border p-4  ">
                    <h6 className="text-lg font-medium mb-3">Order Summary</h6>
                    <table className="w-full text-sm">
                      <tbody>
                        {amount?.discount && amount.discount !== "0.00" && (
                          <>
                            <tr>
                              <td className="py-1">Original Price</td>
                              <td className="text-right">
                                &#8377; {amount.original_price}
                              </td>
                            </tr>
                            <tr>
                              <td className="py-1">Discount</td>
                              <td className="text-right text-green-600">
                                - &#8377; {amount.discount}
                              </td>
                            </tr>
                          </>
                        )}
                        <tr>
                          <td className="py-1">Subtotal</td>
                          <td className="text-right">
                            &#8377; {amount?.sub_total}
                          </td>
                        </tr>
                        {/* {amount?.tax && amount.tax !== "0.00" && (
                          <tr>
                            <td className="py-1">Tax ({amount.tax_rate}%)</td>
                            <td className="text-right">&#8377; {amount.tax}</td>
                          </tr>
                        )} */}
                        {amount?.shipping?.company_rate &&
                          amount.shipping.company_rate !== "0.00" ? (
                            <tr>
                              <td className="py-1">Shipping Charges</td>
                              <td className="text-right">
                                &#8377; {amount.shipping.company_rate}
                              </td>
                            </tr>
                          ) : null}
                        <tr className="font-semibold border-t border-gray-200">
                          <td className="py-2">Total</td>
                          <td className="text-right text-lg">
                            &#8377; {amount?.total}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
                <label className="d-flex align-center flex-wrap mt-3 mb-3">
                  <input
                    className="mr-2"
                    type="checkbox"
                    id="agree"
                    {...register("agree", {
                      required: "You must agree to the terms and conditions",
                    })}
                  />
                  I have read and agree to the{" "}
                  <Link
                    className="ms-1"
                    href={"/terms-and-conditions/"}
                    style={{ textDecoration: "underline" }}
                  >
                    Terms and Condition
                  </Link>
                </label>
                {errors.agree && (
                  <span className="text-red-500 text-md">
                    {errors.agree.message}
                  </span>
                )}
                {Error && <span className="text-red-500 text-md">{Error}</span>}
                <button
                  type="submit"
                  disabled={amount && amount.total === 0}
                  className={`${styles.pay} ${Cart.btn} shine-button mb-4 mt-4`}
                >
                  {paymentMethodType === "ONLINE" ? "Pay Now" : "Buy Now"}
                </button>
              </div>
              {/* Terms & Pay Button */}
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};

export default Checkout;
