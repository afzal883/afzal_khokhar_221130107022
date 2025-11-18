import React from 'react'
import styles from '@/app/(home)/styles/section.module.css'
import Image from 'next/image'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import Cookies from 'universal-cookie'
import { useDispatch } from 'react-redux'
import { addToCart } from '../redux/cartSlice'
import { addWishList } from '../redux/wishListSlice'

const Product2 = ({ data }) => {

    const dispatch = useDispatch();

    const cookies = new Cookies();
    const url = process.env.API_URL;
    const token = cookies.get('token')
    const router = useRouter()

    const availability = data ? data.available && data.stock !== 0 : true;
    if(!availability){
        return
    }

    const handleAddToCart = () => {
        dispatch(addToCart({ quantity: 1, variant_data: data }))
    }

    const handleWishList = () => {        
            dispatch(addWishList(data))
    }

    let slug;
    slug = `/shop/${data.product.slug}/${data.encoded_sku}/${encodeURIComponent(data.product.description.slice(0, 50))}`

    return (
        <div className={styles.item}>
            <Link href={slug || "/shop"}>
                <h4>{data.product.title}</h4>
                <span className={styles.price}>GBP {data && data.discounted_price}</span>
            </Link>
            <Link href={slug || "/shop"} className={styles.image}>
                <Image src={data && data && data.images[0] ? process.env.IMAGE_URL + data.images[0].image : '/images/not_found.png'} className='img-fluid' width={500} height={500} />
            </Link>
            <button disabled={!availability} onClick={handleAddToCart} className={styles.btn}>Add to Cart</button>
        </div>
    )
}

export default Product2
