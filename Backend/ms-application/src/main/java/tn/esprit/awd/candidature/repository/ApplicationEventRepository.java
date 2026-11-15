package tn.esprit.awd.candidature.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import tn.esprit.awd.candidature.entity.ApplicationEvent;

import java.util.List;

public interface ApplicationEventRepository extends JpaRepository<ApplicationEvent, Long> {
    List<ApplicationEvent> findTop50ByOrderByIdAsc();
}
