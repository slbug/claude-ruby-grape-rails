## Controllers

### Modern Controller Structure

```ruby
# app/controllers/api/v1/orders_controller.rb
module Api
  module V1
    class OrdersController < ApplicationController
      before_action :require_authentication
      before_action :set_order, only: %i[show update destroy]
      before_action :authorize_order!, only: %i[update destroy]

      def index
        @orders = current_user.orders
                               .includes(:items)
                               .page(params[:page])
                               .per(20)
        
        render json: @orders
      end

      def show
        render json: @order
      end

      def create
        @order = OrderCreationService.call(
          user: current_user,
          params: order_params
        )
        
        if @order.persisted?
          render json: @order, status: :created
        else
          render json: { errors: @order.errors }, status: :unprocessable_entity
        end
      end

      def update
        if @order.update(order_params)
          render json: @order
        else
          render json: { errors: @order.errors }, status: :unprocessable_entity
        end
      end

      def destroy
        @order.destroy!
        head :no_content
      end

      private

      def set_order
        @order = current_user.orders.find(params[:id])
      rescue ActiveRecord::RecordNotFound
        render json: { error: 'Order not found' }, status: :not_found
      end

      def authorize_order!
        head :forbidden unless @order.user == current_user
      end

      def order_params
        params.require(:order).permit(
          :shipping_address,
          :billing_address,
          items: %i[product_id quantity]
        )
      end
    end
  end
end
```

### Strong Parameters Patterns

```ruby
# Complex nested params
def product_params
  params.require(:product).permit(
    :name,
    :description,
    :price,
    :category_id,
    images: [],
    variants: [
      :size,
      :color,
      :sku,
      inventory: [:quantity, :warehouse_id]
    ],
    metadata: {}
  )
end

# Whitelist approach for APIs
def filter_params
  params.permit(
    :page,
    :per_page,
    :sort,
    :direction,
    filters: [:status, :date_from, :date_to, tags: []]
  ).to_h
end
```
