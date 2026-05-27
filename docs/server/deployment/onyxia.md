# Onyxia

https://datalab.sspcloud.fr is an instance of the Onyxia datalab platform provided by INSEE (France). It is accessible to national statistical offices as a testing ground for data science projects. If you are part of a national statistical office, you can log in to the sspcloud and start a test instance of the Lomas platform.

__Note__: This deployment method is meant for testing only and not safe for production!

To start the lomas-server on Onyxia, folow those steps:

1. __Select the Lomas Service__:
    Within the Onyxia platform, locate the Lomas service.
    You can find the service following this
    [link](https://datalab.sspcloud.fr/catalog/divers)

2. __Customize Parameters (Optional)__:
    Depending on your specific requirements, you may choose to customize the
    administration and runtime parameters. This step allows for fine-tuning the
    deployment according to your project's needs. Onyxia lets you override any part of the Lomas Helm values file. Please refer to the [Kubernetes deployment page](kubernetes.md) for more information.

3. __Initiate Deployment__:
    Once satisfied with the parameter settings, click on the "Lancer" button to
    initiate the deployment process.

4. The Lomas setup job is enabled by default. It adds demo users and datasets to Lomas for testing purposes.

The service notes will provide you with the relevant links to test the service.
