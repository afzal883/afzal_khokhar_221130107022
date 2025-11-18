const axios = require("axios");

function slugify(name) {
    return name
        .toLowerCase()
        .replace(/\s+/g, '-')
        .replace(/[^\w\-]+/g, '') // remove special chars
        .replace(/\-\-+/g, '-')
        .replace(/^-+|-+$/g, '');
}

/** @type {import('next-sitemap').IConfig} */
module.exports = {
    siteUrl: 'https://www.iconperfumes.in',
    generateRobotsTxt: true,
    changefreq: 'daily',
    priority: 0.7,
    sitemapSize: 5000,
    outDir: './public',
    additionalPaths: async () => {
        try {
            const res = await axios.get(`${process.env.API_URL}/categories`);
            const categories = res.data.categories || [];

            const categoryMap = {};
            const urls = [];

            // Step 1: Create a map of ID to category slug
            for (const cat of categories) {
                categoryMap[cat.id] = slugify(cat.name);
            }

            // Step 2: Generate URL paths based on parent-child structure
            for (const cat of categories) {
                const slug = slugify(cat.name);

                let loc = `/${slug}`; // default path

                if (cat.parent && categoryMap[cat.parent]) {
                    const parentSlug = categoryMap[cat.parent];
                    loc = `/${parentSlug}/${slug}`; // nested path
                }

                urls.push({
                    loc,
                    lastmod: new Date().toISOString(),
                });
            }

            return urls;
        } catch (err) {
            console.error("❌ Error generating category sitemap:", err.message);
            return [];
        }
    },
};
