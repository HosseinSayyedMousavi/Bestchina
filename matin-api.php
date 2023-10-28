<?php
/*
Plugin Name: وبسرویس ویژه
Plugin URI: https://wpmatin.ir
Description:
Author:  متین وفادوست
Version: 1.0.0
Text Domain: wpapi
Author URI: https://wpmatin.ir
*/
#--- Designed and developed by Hampo | Matin Vafadoost ---#

if (!defined('ABSPATH')) {
    die();
}
function custom_api_endpoint() {
    register_rest_route('wpapi/v1', '/show-existence', array(
        'methods' => 'POST',
        'callback' => 'custom_api_callback',
    ));
}
add_action('rest_api_init', 'custom_api_endpoint');
function custom_api_callback($request) {
    global $wpdb;

    $parameters = $request->get_params();
    
    // $product_id = $parameters['product_id'];
    // $product = wc_get_product($product_id);
   
    
    // $product_data = array(
    //     'product_id' => $product->get_id(),
    //     'product_name' => $product->get_name(),
    //     'product_price' => $product->get_price(),
    //     'product_sku' => $product->get_sku(),
    //     // دیگر اطلاعات مورد نظر
    // );
    
$product_shenase = $parameters['ItemNo']; 
$sql = $wpdb->prepare("SELECT p.ID
FROM {$wpdb->prefix}posts AS p
INNER JOIN {$wpdb->prefix}postmeta AS pm ON p.ID = pm.post_id
WHERE p.post_type = 'product'
AND p.post_status = 'publish'
AND pm.meta_key = '_sku'
AND pm.meta_value = %s", $product_shenase);
$product_id = $wpdb->get_var($sql);

if ($product_id) {

$product = wc_get_product($product_id);
$product_data = array('response' => true);
}
else {
    // محصول با SKU مورد نظر یافت نشد
    $product_data = array('response' => false);
}
     
    return new WP_REST_Response($product_data, 200);
}









add_action('rest_api_init', function () {
    register_rest_route('wpapi/v1', '/create-update-product', array(
        'methods' => 'POST',
        'callback' => function ($request) {
            global $wpdb;
            $data = $request->get_json_params();
            file_put_contents(__DIR__ . DIRECTORY_SEPARATOR . 'request.json', json_encode($data) . PHP_EOL, FILE_APPEND);
            $product_data = $data['Detail'];
            
            #---[set or update product]---#
            $product_id = 0;
            $product_sql = $wpdb->get_results(" SELECT wp_posts.ID  FROM wp_postmeta,wp_posts WHERE wp_postmeta.meta_value = '" . $product_data['ItemNo'] . "' AND wp_postmeta.meta_key = '_sku' AND wp_postmeta.post_id = wp_posts.ID AND wp_posts.post_type = 'product' AND wp_posts.post_status = 'publish';");
            if (!empty($product_sql)) {
                $product_id = $product_sql[0]->ID;
            }
            $update = $product_id != 0;

            if ($update) {
                $product = new WC_Product_Simple($product_id);
            } else {
                $product = new WC_Product_Simple();
            }

            $product->set_length($product_data['Length']);
            $product->set_width($product_data['Width']);
            $product->set_height($product_data['Height']);
            $product->set_regular_price($product_data['OriginalPrice']);
            $product->set_sku($product_data['ItemNo']);
            $product->set_stock_status($product_data['ProductStatus'] ? 'instock' : 'outofstock');
            $product->set_status('publish');
            $product->set_name($product_data['Name']);
            $product->set_description($product_data['Description']);
            if (!empty($product_data['MOQ'])) {
                $product->update_meta_data('_minimum_quantity_order', $product_data['MOQ']);
            }
            if (!empty($product_data['MXOQ'])) {
                $product->update_meta_data('_maximum_quantity_order', $product_data['MXOQ']);
            }
            $product->save();
            $product_id = $product->get_id();

            if (!empty($product_data['CategoryCode']) && is_array($product_data['CategoryCode'])) {
                $category_ids = [];
                foreach ($product_data['CategoryCode'] as $categoryCode) {
                    $category_term = $wpdb->get_results("SELECT term_id FROM `wp_termmeta` WHERE `meta_value` = '" . $categoryCode . "';");
                    if (!empty($category_term)) {
                        $category_ids[] = $category_term[0]->term_id;
                    }
                }
                wp_set_post_terms($product_id, $category_ids, 'product_cat');
            }


            if (!empty($data['ModelList'])) {
                $attr = [];
                foreach ($data['ModelList'] as $key => $item) {
                    foreach ((array)$item['Attributes'] as $key => $val) {
                        $attr[$key][] = $val;
                    }
                }
                foreach ($attr as $key => $items) {
                    $attribute = new WC_Product_Attribute();
                    $attribute->set_name($key);
                    $attribute->set_id(0);
                    $attribute->set_visible(true);
                    $attribute->set_variation(true);
                    $attribute->set_options(array_unique($items));
                    $attributes[] = $attribute;
                }
                $product = new WC_Product_Variable();
                $product->set_id($product_id);
                $product->set_attributes($attributes);
                $product->save();
                #-- variation info --#
                foreach ($data['ModelList'] as $key => $item) {
                    $variation = new WC_Product_Variation();
//                    $variation_id = wc_get_product_id_by_sku($item['ItemNo']);
//                    if ($variation_id) {
//                        $variation->set_id($variation_id);
//                    }
                    $variation->set_parent_id($product_id);
                    $variation->set_regular_price($item['OriginalPrice']);
                    if (!empty($item['MOQ'])) {
                        $variation->update_meta_data('_minimum_quantity_order', $item['MOQ']);
                    }
                    if (!empty($item['MXOQ'])) {
                        $variation->update_meta_data('_maximum_quantity_order', $item['MXOQ']);
                    }
                    

                    $gallery = upload_and_extract_images($item['Image'], 1, $item['ItemNo']);
                    if (!empty($gallery[0])) {
                        $variation->set_image_id($gallery[0]);
                    }


                    foreach ($item['Attributes'] as $attr_key => $attr_value) {
                        $variation->update_meta_data('attribute_' . strtolower(urlencode(str_replace([' '], ['-'], $attr_key))), $attr_value);
                    }
                    //$variation->set_attributes(urlEncodeArray($item['Attributes']));
                    $variation->save();
                }
            }

            if (!empty($data['AddonList'])) {
                foreach ($data['AddonList'] as $key => $item) {
                    $options = [];
                    foreach ($item['Options'] as $option) {
                        $options[] = [
                            'label' => $option['Label'],
                            'price' => $option['Price'],
                            'image' => '',
                            'price_type' => 'flat_fee',
                        ];
                    }

                    $fields[] = [
                        'name' => $item['Name'],
                        'title_format' => 'label',
                        'description' => $item['Description'],
                        'type' => 'multiple_choice',
                        'display' => 'select',
                        'position' => 0,
                        'required' => 1,
                        'restrictions' => 0,
                        'restrictions_type' => 'any_text',
                        'adjust_price' => 0,
                        'price_type' => 'flat_fee',
                        'price' => null,
                        'min' => 0,
                        'max' => 0,
                        'description_enable' => !empty($item['Description']) ? 1 : 0,
                        'options' => $options
                    ];

                    $result = WC_Product_Addons_Groups::update_group(
                        $product_id,
                        [
                            'fields' => $fields
                        ]
                    );
                }
            }

            if (!$update) {
                $gallery_images = upload_and_extract_images($product_data['Image'], 10, 'gallery_' . $product_data['ItemNo']);
                update_post_meta($product_id, '_product_image_gallery', implode(',', $gallery_images));
            }
            #---[set thumbnail]---#
            if (!empty($gallery_images)) {
                set_post_thumbnail($product_id, $gallery_images[0]);
            }

            $gallery_ids = get_post_meta($product_id, '_product_image_gallery', true);
            if (!empty($gallery_ids)) {
                $gallery_htmls = explode(',', $gallery_ids);
                #---[image html]---#
                array_walk($gallery_htmls, function (&$item) {
                    $item = wp_get_attachment_image($item, 'full', "", array("class" => "img-responsive"));
                });
                wp_update_post([
                    'ID' => $product_id,
                    'post_content' => $product_data['Description'] . implode('', $gallery_htmls),
                ]);
            }

            // wc_delete_product_transients($product_id);

            return rest_ensure_response([
                'result' => $product_id !== 0,
                'product_id' => $product_id
            ]);
        },
        'permission_callback' => '__return_true', // یا تنظیم مجوز مورد نیاز
    ));
});


add_action('rest_api_init', function () {
    register_rest_route('wpapi/v1', 'create-update-category', array(
        'methods' => 'POST',
        'callback' => function ($request) {
            global $wpdb;
            $categories_data = $request->get_json_params();
            foreach ($categories_data as $category_data) {
                $parent_id = 0; // برای دسته‌بندی‌های اصلی، پدر مشخص نشده است
                $parent_code = $category_data['ParentCode'];
                if (!empty($parent_code)) {
                    $category_parent_term = $wpdb->get_results("SELECT term_id FROM `wp_termmeta` WHERE `meta_value` = '" . $parent_code . "';");
                    if (!empty($category_parent_term)) {
                        $parent_id = $category_parent_term[0]->term_id;
                    }
                }
                $category_args = array(
                    'parent' => $parent_id,
                );
                $code = false;
                $category_term = $wpdb->get_results("SELECT term_id FROM `wp_termmeta` WHERE `meta_value` = '" . $category_data['Code'] . "';");
                if (!empty($category_term)) {
                    $code = $category_term[0]->term_id;
                }

                if ($code) {
                    $category_args['name'] = $category_data['Name'];
                    wp_update_term($code, 'product_cat', $category_args);
                } else {
                    $category_args['name'] = $category_data['Name'];
                    $term_id = wp_insert_term($category_data['Name'], 'product_cat', $category_args);
                    // اضافه کردن متا اطلاعات
                    if (!is_wp_error($term_id)) {
                        add_term_meta($term_id['term_id'], 'Code', $category_data['Code'], true);
                    }
                }
            }

            return new WP_REST_Response(array('message' => 'categories created/updated successfully.'), 200);
        }
    ));
});

function custom_price_widget()
{
    wp_add_dashboard_widget(
        'custom_price_widget',
        __('محاسبه قیمت با توجه به قیمت دلار', 'your-textdomain'),
        'custom_price_widget_content'
    );
}

add_action('wp_dashboard_setup', 'custom_price_widget');
function custom_price_widget_content()
{
    if (isset($_POST['custom_price_multiplier'])) {
        update_option('custom_price_multiplier', $_POST['custom_price_multiplier']);
    }
    $multiplier = get_option('custom_price_multiplier', 1);
    $product_price = 100; // مقدار دلخواه
    $calculated_price = $product_price * $multiplier;
    ?>
    <style>
        div#custom_price_widget button.button.button-primary {
            width: 100%;
            margin-bottom: 10px;
        }

        div#custom_price_widget label, div#custom_price_widget input#custom_price_multiplier {
            width: 100% !important;
        }

        div#custom_price_widget label {
            margin-bottom: 7px !important;
            display: block;
        }

        div#custom_price_widget input#custom_price_multiplier {
            margin-bottom: 10px;
        }

        div#custom_price_widget .example {
            background: #ddd;
            padding: 1px 8px;
            text-align: center;
            border-radius: 3px;
        }

        div#custom_price_widget .example p {
            background: #fff;
            padding: 3px;
        }
    </style>
    <?php
    echo '<form method="post">';
    echo '<div>';
    echo '<label for="custom_price_multiplier">' . __('قیمت دلار:', 'your-textdomain') . '</label>';
    echo '<input type="number" id="custom_price_multiplier" name="custom_price_multiplier" value="' . esc_attr($multiplier) . '">';
    echo '</div>';
    echo '<button type="submit" class="button button-primary">' . __('ذخیره', 'your-textdomain') . '</button>';
    echo '</form>';
    echo '<div class="example">';
    echo '<p>' . __('قیمت محصول:', 'your-textdomain') . ' ' . number_format($product_price) . 'دلار </p>';
    echo '<p>' . __('قیمت محصول با توجه به قیمت دلار :', 'your-textdomain') . ' ' . wc_price($calculated_price) . '</p>';
    echo '</div>';
}

function upload_and_extract_images($zip_url, $limit = 5, $itemNo = 'terminal')
{
    $upload_dir = wp_upload_dir();
    $zip_file = download_url($zip_url);

    if (is_wp_error($zip_file)) {
        return false;
    }

    $extract_path = $upload_dir['basedir'] . '/extracted_images/' . $itemNo . '/';
    wp_mkdir_p($extract_path);

    $extracted = unzip_file($zip_file, $extract_path);
    unlink($zip_file);

    if (is_wp_error($extracted)) {
        return false;
    }

    $image_ids = array();
    $extracted_files = scandir($extract_path);
    $i = 1;
    sort($extracted_files);
    foreach ($extracted_files as $file) {

        if ('.' === $file || '..' === $file || $i > $limit) {
            continue;
        }
        $file_array = explode('-', $file);
        if (count($file_array) > 1) {
            continue;
        }


        $file_path = $extract_path . $file;
        $file_info = pathinfo($file_path);
        $image_title = sanitize_file_name($file_info['filename']);

        $attachment = array(
            'guid' => $upload_dir['url'] . '/' . $file,
            //'post_mime_type' => wp_check_filetype($file),
            'post_mime_type' => 'image/jpeg',
            'post_title' => $image_title,
            'post_content' => '',
            'post_status' => 'inherit',
        );
        $attachment_id = wp_insert_attachment($attachment, $file_path);
        if (!is_wp_error($attachment_id)) {
            $image_ids[] = $attachment_id;
            require_once(ABSPATH . 'wp-admin/includes/image.php');
            $attachment_data = wp_generate_attachment_metadata($attachment_id, $file_path);
            wp_update_attachment_metadata($attachment_id, $attachment_data);
            $i++;
        }

    }
    return $image_ids;
}

function urlEncodeArray($array)
{
    $encodedArray = array();
    foreach ($array as $key => $value) {
        $encodedKey = strtolower(urlencode($key));
        $encodedArray[$encodedKey] = $value;
    }
    return $encodedArray;
}


// Simple, grouped and external products
add_filter('woocommerce_product_get_price', 'custom_price', 99, 2);
add_filter('woocommerce_product_get_regular_price', 'custom_price', 99, 2);
// Variations
add_filter('woocommerce_product_variation_get_regular_price', 'custom_price', 99, 2);
add_filter('woocommerce_product_variation_get_price', 'custom_price', 99, 2);
function custom_price($price, $product)
{
    $multiplier = get_option('custom_price_multiplier', 1);
    $number = $price * $multiplier;
    return floor($number / 10000) * 10000;
}

// Variable (price range)
add_filter('woocommerce_variation_prices_price', 'custom_variable_price', 99, 3);
add_filter('woocommerce_variation_prices_regular_price', 'custom_variable_price', 99, 3);
function custom_variable_price($price, $variation, $product)
{
    // Delete product cached price  (if needed)
    // wc_delete_product_transients($variation->get_id());
    $multiplier = get_option('custom_price_multiplier', 1);
    $number = $price * $multiplier;
    return floor($number / 10000) * 10000;
}

// Handling price caching (see explanations at the end)
add_filter('woocommerce_get_variation_prices_hash', 'add_price_multiplier_to_variation_prices_hash', 99, 3);
function add_price_multiplier_to_variation_prices_hash($price_hash, $product, $for_display)
{
    $price_hash[] = get_option('custom_price_multiplier', 1);
    return $price_hash;
}

add_filter('woocommerce_product_addons_option_price_raw', 'custom_addon_price', 99, 1);
function custom_addon_price($price)
{
    $multiplier = get_option('custom_price_multiplier', 1);
    $number = $price * $multiplier;
    return floor($number / 10000) * 10000;
}


add_filter('woocommerce_get_item_data', 'get_item_data', 99, 2);
function get_item_data($other_data, $cart_item)
{
    if (!empty($cart_item['addons'])) {
        $multiplier = get_option('custom_price_multiplier', 1);
        foreach ($other_data as $key => $data) {
            if (str_contains($data['name'], 'ارسال')) {
                unset($other_data[$key]);
            }
        }
        foreach ($cart_item['addons'] as $addon) {
            $price = isset($cart_item['addons_price_before_calc']) ? $cart_item['addons_price_before_calc'] : $addon['price'];
            $name = $addon['name'];
            $number = $addon['price'] * $multiplier;
            $addon['price'] = floor($number / 10000) * 10000;
            if (0 == $addon['price']) {
                $name .= '';
            } elseif ('percentage_based' === $addon['price_type'] && 0 == $price) {
                $name .= '';
            } elseif ('percentage_based' !== $addon['price_type'] && $addon['price'] && apply_filters('woocommerce_addons_add_price_to_name', true)) {
                $name .= ' (' . wc_price(WC_Product_Addons_Helper::get_product_addon_price_for_display($addon['price'], $cart_item['data'], true)) . ')';
            } else if (apply_filters('woocommerce_addons_add_price_to_name', true)) {
                $_product = wc_get_product($cart_item['product_id']);
                $_product->set_price($price * ($addon['price'] / 100));
                $name .= ' (' . WC()->cart->get_product_price($_product) . ')';
            }

            $addon_data = array(
                'name' => $name,
                'value' => $addon['value'],
                'display' => isset($addon['display']) ? $addon['display'] : '',
            );
            $other_data[] = apply_filters('woocommerce_product_addons_get_item_data', $addon_data, $addon, $cart_item);
        }
    }

    return $other_data;
}

add_action('woocommerce_checkout_create_order_line_item', 'order_line_item', 10, 3);
function order_line_item($item, $cart_item_key, $values)
{
    if (!empty($values['addons'])) {
        $ids = array();

        foreach ($values['addons'] as $addon) {
            $key = $addon['name'];
            $price_type = $addon['price_type'];
            $product = $item->get_product();
            $product_price = $product->get_price();

            if ($addon['price'] && 'percentage_based' === $price_type && 0 != $product_price) {
                $addon_price = $product_price * ($addon['price'] / 100);
            } else {
                $addon_price = $addon['price'];
            }
            $multiplier = get_option('custom_price_multiplier', 1);
            $number = $addon_price * $multiplier;
            $addon_price = floor($number / 10000) * 10000;
            $price = html_entity_decode(
                strip_tags(wc_price(WC_Product_Addons_Helper::get_product_addon_price_for_display($addon_price, $values['data']))),
                ENT_QUOTES,
                get_bloginfo('charset')
            );

            /*
             * If there is an add-on price, add the price of the add-on
             * to the label name.
             */
            if ($addon['price'] && apply_filters('woocommerce_addons_add_price_to_name', true)) {
                $key .= ' (' . $price . ')';
            }

            if ('custom_price' === $addon['field_type']) {
                $addon['value'] = $addon['price'];
            }

            $meta_data = [
                'key' => $key,
                'value' => $addon['value'],
                'id' => $addon['id']
            ];
            $meta_data = apply_filters('woocommerce_product_addons_order_line_item_meta', $meta_data, $addon, $item, $values);

            $item->add_meta_data($meta_data['key'], $meta_data['value']);

            $ids[] = $meta_data;
        }

        $item->add_meta_data('_pao_ids', $ids);
    }
}


add_filter('woocommerce_add_to_cart_validation', 'minimum_quantity_order', 10, 4);
function minimum_quantity_order($passed, $product_id, $quantity, $variation_id = null)
{
    $pid = empty($variation_id) ? $product_id : $variation_id;
    $min_quantity = get_post_meta($pid, '_minimum_quantity_order', true);
    $max_quantity = get_post_meta($pid, '_maximum_quantity_order', true);
    if (!empty($min_quantity) && $min_quantity > 0 && empty($max_quantity)) {
        if ($quantity < $min_quantity) {
            $passed = false;
            wc_add_notice('حداقل تعداد سفارش بایستی ' . number_format($min_quantity) . ' عدد باشد', 'error');
        }
    }
    if (!empty($max_quantity) && $max_quantity > 0 && empty($min_quantity)) {
        if ($quantity > $max_quantity) {
            $passed = false;
            wc_add_notice('حداکثر تعداد سفارش بایستی ' . number_format($max_quantity) . ' عدد باشد', 'error');
        }
    }
    if (!empty($max_quantity) && !empty($min_quantity) && $min_quantity > 0 && $max_quantity > $min_quantity) {
        if ($quantity > $max_quantity || $quantity < $min_quantity) {
            $passed = false;
            wc_add_notice('تعداد سفارش بایستی بین ' . number_format($min_quantity) . ' تا ' . number_format($max_quantity) . ' عدد باشد', 'error');
        }
    }


    return $passed;
}


// Display Fields
add_action('woocommerce_product_options_general_product_data', 'woocommerce_product_custom_fields');
// Save Fields
add_action('woocommerce_process_product_meta', 'woocommerce_product_custom_fields_save');
function woocommerce_product_custom_fields()
{
    global $woocommerce, $post;
    echo '<div class="product_custom_field">';
    woocommerce_wp_text_input(
        array(
            'id' => '_minimum_quantity_order',
            'placeholder' => 'حدااقل تعداد سفارش',
            'label' => __('حدااقل تعداد سفارش', 'woocommerce'),
            'type' => 'number',
            'custom_attributes' => array(
                'step' => 'any',
            )
        )
    );
    woocommerce_wp_text_input(
        array(
            'id' => '_maximum_quantity_order',
            'placeholder' => 'حداکثر تعداد سفارش',
            'label' => __('حداکثر تعداد سفارش', 'woocommerce'),
            'type' => 'number',
            'custom_attributes' => array(
                'step' => 'any',
            )
        )
    );
    echo '</div>';
}

function woocommerce_product_custom_fields_save($post_id)
{
    update_post_meta($post_id, '_minimum_quantity_order', $_POST['_minimum_quantity_order']);
    update_post_meta($post_id, '_maximum_quantity_order', $_POST['_maximum_quantity_order']);
}