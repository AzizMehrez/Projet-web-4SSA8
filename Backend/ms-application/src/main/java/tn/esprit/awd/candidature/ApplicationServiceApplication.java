package tn.esprit.awd.candidature;

import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.cloud.openfeign.EnableFeignClients;
import org.springframework.context.annotation.Bean;
import org.springframework.scheduling.annotation.EnableScheduling;
import feign.Retryer;

@SpringBootApplication
@EnableDiscoveryClient
@EnableScheduling
@EnableFeignClients(defaultConfiguration = ApplicationServiceApplication.FeignRetries.class)
public class ApplicationServiceApplication {

    public static void main(String[] args) {
        org.springframework.boot.SpringApplication.run(ApplicationServiceApplication.class, args);
    }

    static class FeignRetries {
        @Bean
        Retryer applicationFeignRetryer() {
            return new Retryer.Default(100, 300, 3);
        }
    }
}
