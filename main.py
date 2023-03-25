from flask import Flask
from flask_keycloak_secure import FlaskKeycloakSecure
from flask_graphql import GraphQLView
from graphene import (
    ObjectType,
    String,
    List,
    ID,
    InputObjectType,
    Field,
    Schema,
    Mutation,
)
from flask_sqlalchemy import SQLAlchemy

# Import the necessary Stripe API libraries
import stripe


app = Flask(__name__)
app.config.from_object("config")

keycloak_secure = FlaskKeycloakSecure(app)

# Set up SQLAlchemy
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///todos.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# Define the TodoItem model
class TodoItemModel(db.Model):
    __tablename__ = "todo_items"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    time = db.Column(db.String(20))
    image = db.Column(db.String(255))

    def __repr__(self):
        return "<TodoItem %r>" % self.title


# Define the TodoItem GraphQL type
class TodoItem(ObjectType):
    id = ID(required=True)
    title = String(required=True)
    description = String()
    time = String()
    image = String()


# Define the Query GraphQL type
class Query(ObjectType):
    all_todo_items = List(TodoItem)

    def resolve_all_todo_items(self, info):
        # Retrieve all TodoItems from the database
        todo_items = TodoItemModel.query.all()
        # Convert each TodoItem to a TodoItem GraphQL object
        return [
            TodoItem(
                id=item.id,
                title=item.title,
                description=item.description,
                time=item.time,
                image=item.image,
            )
            for item in todo_items
        ]


# Define the TodoItemInput GraphQL input type
class TodoItemInput(InputObjectType):
    title = String(required=True)
    description = String()
    time = String()
    image = String()


# Define the CreateTodoItem mutation resolver
class CreateTodoItem(Mutation):
    class Arguments:
        input = TodoItemInput(required=True)

    todo_item = Field(TodoItem)

    def mutate(self, info, input):
        # Create a new TodoItem in the database
        todo_item = TodoItemModel(
            title=input.title,
            description=input.description,
            time=input.time,
            image=input.image,
        )
        db.session.add(todo_item)
        db.session.commit()
        # Return the new TodoItem as a TodoItem GraphQL object
        return CreateTodoItem(
            todo_item=TodoItem(
                id=todo_item.id,
                title=todo_item.title,
                description=todo_item.description,
                time=todo_item.time,
                image=todo_item.image,
            )
        )


# Define the UpdateTodoItem mutation resolver
class UpdateTodoItem(Mutation):
    class Arguments:
        id = ID(required=True)
        input = TodoItemInput(required=True)

    todo_item = Field(TodoItem)

    def mutate(self, info, id, input):
        # Retrieve the specified TodoItem from the database
        todo_item = TodoItemModel.query.get(id)
        if not todo_item:
            raise Exception("TodoItem not found")
        # Update the TodoItem in the database
        todo_item.title = input.title
        todo_item.description = input.description
        todo_item.time = input.time
        todo_item.image = input.image
        db.session.commit()
        # Return the updated TodoItem as a TodoItem GraphQL object
        return UpdateTodoItem(
            todo_item=TodoItem(
                id=todo_item.id,
                title=todo_item.title,
                description=todo_item.description,
                time=todo_item.time,
                image=todo_item.image,
            )
        )


# Define the DeleteTodoItem mutation resolver
class DeleteTodoItem(Mutation):
    class Arguments:
        id = ID(required=True)

    ok = Field(String)

    def mutate(self, info, id):
        # Retrieve the specified TodoItem from the database
        todo_item = TodoItemModel.query.get(id)
        if not todo_item:
            raise Exception("TodoItem not found")
        # Delete the TodoItem from the database
        db.session.delete(todo_item)
        db.session.commit()
        # Return a success message
        return DeleteTodoItem(ok="TodoItem deleted")


# Set up the Stripe API key
stripe.api_key = "your-stripe-api-key"


# Define the Mutation GraphQL type
class Mutation(ObjectType):
    create_todo_item = CreateTodoItem.Field()
    update_todo_item = UpdateTodoItem.Field()
    delete_todo_item = DeleteTodoItem.Field()

    # Define the Stripe Checkout mutation resolver
    class Checkout(Mutation):
        class Arguments:
            success_url = String(required=True)
            cancel_url = String(required=True)

        # Define the return fields for the mutation
        session_id = String()

        def mutate(self, info, success_url, cancel_url):
            # Create a new Stripe Checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "unit_amount": 500,
                            "product_data": {
                                "name": "Pro License",
                                "images": ["https://example.com/pro-license.png"],
                            },
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
            )

            # Return the session ID to the client
            return Checkout(session_id=session.id)


# Define the GraphQL schema
schema = Schema(query=Query, mutation=Mutation)

# Add the GraphQL view to the Flask app
app.add_url_rule(
    "/graphql", view_func=GraphQLView.as_view("graphql", schema=schema, graphiql=True)
)

if __name__ == "__main__":
    app.run()
